from datetime import date, datetime, timezone
import math

from flask import Blueprint, jsonify, request

import config
import database
import schedule
import telegram_api
import texts
from mini_app_auth import verify_init_data

bp = Blueprint("mini_app_api", __name__, url_prefix="/api")

REQUEST_STATUSES = {
    "pending",
    "confirmed",
    "rejected",
    "cancelled",
    "expired",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@bp.errorhandler(ApiError)
def _api_error(error: ApiError):
    response = jsonify(
        {"ok": False, "error": {"code": error.code, "message": error.message}}
    )
    response.status_code = error.status
    response.headers["Cache-Control"] = "no-store"
    return response


def _json() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Очікується JSON-об'єкт.")
    return data


def _text_field(data: dict, name: str, max_length: int) -> str:
    value = data.get(name)
    if not isinstance(value, str):
        raise ApiError(400, "invalid_field", f"Поле {name} має бути рядком.")
    value = value.strip()
    if not value or len(value) > max_length:
        raise ApiError(400, "invalid_field", f"Некоректне поле {name}.")
    return value


def _init_data() -> str:
    value = request.headers.get("X-Telegram-Init-Data", "").strip()
    if not value:
        authorization = request.headers.get("Authorization", "").strip()
        if authorization.lower().startswith("tma "):
            value = authorization[4:].strip()
    return value


def _current_user() -> dict:
    user = verify_init_data(_init_data(), config.BOT_TOKEN)
    if user is None:
        raise ApiError(401, "unauthorized", "Відкрийте застосунок через Telegram.")
    return user


def _current_admin() -> dict:
    user = _current_user()
    if not config.is_admin(user["id"]):
        raise ApiError(403, "forbidden", "Доступ лише для адміністратора.")
    return user


def _iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return value
    return parsed.isoformat().replace("+00:00", "Z")


def _expires_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def _booking_json(booking: dict, viewer_id: int, admin: bool = False) -> dict:
    owned = booking.get("user_id") == viewer_id
    expires = _expires_at(booking.get("expires_at"))
    hold_active = (
        booking.get("status") == database.STATUS_HELD
        and expires is not None
        and expires > datetime.now(timezone.utc)
    )
    payload = {
        "id": booking["id"],
        "service_id": booking["service_id"],
        "service_name": booking["service_name"],
        "price": booking.get("price_label", ""),
        "duration_minutes": booking.get("duration_minutes", 60),
        "date_id": booking["date_id"],
        "date_label": booking["date_label"],
        "time_id": booking["time_id"],
        "time_label": booking["time_label"],
        "status": booking["status"],
        "status_label": texts.booking_status_label(booking["status"]),
        "expires_at": _iso(booking.get("expires_at")),
        "created_at": _iso(booking.get("created_at")),
        "can_cancel": owned and not admin and schedule.can_cancel(booking),
        "can_submit": owned and not admin and hold_active,
    }
    if admin:
        payload["client"] = texts.client_label(booking)
        payload["user_id"] = booking.get("user_id")
    return payload


def _service(service_id: str) -> dict:
    service = config.SERVICES_BY_ID.get(service_id)
    if service is None:
        raise ApiError(400, "unknown_service", "Послугу не знайдено.")
    return service


def _validate_date(date_id: str) -> None:
    try:
        date.fromisoformat(date_id)
    except ValueError as exc:
        raise ApiError(400, "invalid_date", "Некоректна дата.") from exc
    if not schedule.is_within_booking_window(date_id):
        raise ApiError(400, "date_unavailable", "Дата поза доступним періодом.")
    if not schedule.is_working_date(date_id):
        raise ApiError(400, "date_unavailable", "У цей день салон не працює.")


def _slot_state(date_id: str, service: dict, time_id: str) -> str:
    if time_id not in {label for label, _start in schedule.slot_grid(date_id)}:
        return "unavailable"
    start = schedule.time_to_minutes(time_id)
    if start is None or not schedule.can_fit(date_id, service, start):
        return "unavailable"
    start_at = schedule.appointment_start({"date_id": date_id, "time_id": time_id})
    if start_at is None or start_at <= schedule.current_time():
        return "past"
    duration = int(service.get("duration_minutes", 60))
    occupied = database.get_occupied_intervals(date_id)
    if any(
        schedule.overlaps(start, start + duration, occupied_start, occupied_end)
        for occupied_start, occupied_end in occupied
    ):
        return "booked"
    return "free"


def _slots(date_id: str, service: dict) -> list[dict]:
    duration = int(service.get("duration_minutes", 60))
    result = []
    now = schedule.current_time()
    occupied = database.get_occupied_intervals(date_id)
    for label, start in schedule.slot_grid(date_id):
        fits = schedule.can_fit(date_id, service, start)
        start_at = schedule.appointment_start({"date_id": date_id, "time_id": label})
        if not fits:
            state = "unavailable"
        elif start_at is None or start_at <= now:
            state = "past"
        elif any(
            schedule.overlaps(start, start + duration, occupied_start, occupied_end)
            for occupied_start, occupied_end in occupied
        ):
            state = "booked"
        else:
            state = "free"
        result.append(
            {
                "id": label,
                "label": label,
                "end": schedule.format_clock(start + duration) if fits else None,
                "status": state,
            }
        )
    return result


def _date_payload(date_id: str) -> dict:
    return {"id": date_id, "label": schedule.date_label(date_id)}


@bp.get("/config")
def config_endpoint():
    user = _current_user()
    return jsonify(
        {
            "ok": True,
            "data": {
                "salon": {
                    "name": config.SALON_NAME,
                    "city": config.CITY,
                    "address": config.ADDRESS,
                    "phone": config.PHONE,
                    "phone_uri": config.PHONE_URI,
                    "instagram": config.INSTAGRAM_URL,
                    "working_hours": config.WORKING_HOURS,
                    "timezone": config.TIMEZONE,
                },
                "user": {
                    "id": user["id"],
                    "first_name": user.get("first_name", ""),
                    "username": user.get("username", ""),
                },
                "services": list(config.SERVICES),
                "hold_ttl_seconds": config.HOLD_TTL_SECONDS,
                "cancellation_cutoff_minutes": config.CANCELLATION_CUTOFF_MINUTES,
                "booking_days_ahead": config.BOOKING_DAYS_AHEAD,
                "is_admin": config.is_admin(user["id"]),
            },
        }
    )


@bp.get("/availability")
def availability_endpoint():
    user = _current_user()
    service_id = request.args.get("service_id", "").strip()
    service = _service(service_id)
    date_id = request.args.get("date", "").strip()
    if not date_id:
        dates = schedule.available_dates(
            service,
            occupied_lookup=database.get_occupied_intervals,
        )
        return jsonify(
            {
                "ok": True,
                "data": {
                    "service": service,
                    "dates": [
                        {"id": item_id, "label": label}
                        for item_id, label in dates
                    ],
                },
            }
        )
    _validate_date(date_id)
    return jsonify(
        {
            "ok": True,
            "data": {
                "service": service,
                "date": _date_payload(date_id),
                "slots": _slots(date_id, service),
            },
        }
    )


@bp.post("/holds")
def create_hold_endpoint():
    user = _current_user()
    data = _json()
    service = _service(_text_field(data, "service_id", 40))
    date_id = _text_field(data, "date", 10)
    time_id = _text_field(data, "time", 5)
    _validate_date(date_id)
    state = _slot_state(date_id, service, time_id)
    if state in ("past", "unavailable"):
        raise ApiError(409, "slot_unavailable", "Цей час недоступний. Оберіть інший.")
    token = request.headers.get("Idempotency-Key", "").strip()
    if len(token) > 80:
        raise ApiError(400, "invalid_idempotency_key", "Некоректний ключ повтору.")
    username = str(user.get("username") or user.get("first_name") or "")[:64]
    hold = database.create_hold(
        user_id=user["id"],
        username=username,
        service=service,
        slot_date={"id": date_id, "label": schedule.date_label(date_id)},
        slot_time={"id": time_id, "label": time_id},
        client_token=token,
    )
    if hold is None:
        raise ApiError(409, "slot_taken", "Цей час уже зайнятий. Оберіть інший.")
    if hold["status"] != database.STATUS_HELD:
        raise ApiError(
            409,
            "hold_inactive",
            "Ця спроба вже неактуальна. Оновіть вільні слоти.",
        )
    return jsonify(
        {
            "ok": True,
            "data": {
                "booking": _booking_json(hold, user["id"]),
                "hold_ttl_seconds": config.HOLD_TTL_SECONDS,
                "idempotent": bool(hold.get("idempotent")),
            },
        }
    )


@bp.post("/holds/<int:hold_id>/submit")
def submit_hold_endpoint(hold_id: int):
    user = _current_user()
    submitted = database.submit_hold(hold_id, user["id"])
    if submitted is None:
        current = database.get_booking(hold_id)
        if current is None or current.get("user_id") != user["id"]:
            raise ApiError(404, "not_found", "Утримання не знайдено.")
        if current.get("status") in (database.STATUS_PENDING, database.STATUS_CONFIRMED):
            return jsonify(
                {"ok": True, "data": {"booking": _booking_json(current, user["id"])}}
            )
        raise ApiError(
            409,
            "hold_expired",
            "Утримання вже неактивне. Оберіть час ще раз.",
        )
    telegram_api.notify_new_request(submitted)
    return jsonify(
        {"ok": True, "data": {"booking": _booking_json(submitted, user["id"])}}
    )


@bp.delete("/holds/<int:hold_id>")
def release_hold_endpoint(hold_id: int):
    user = _current_user()
    current = database.get_booking(hold_id)
    if current is None or current.get("user_id") != user["id"]:
        raise ApiError(404, "not_found", "Утримання не знайдено.")
    if current.get("status") == database.STATUS_CANCELLED:
        return jsonify({"ok": True, "data": {"released": True}})
    if not database.release_hold(hold_id, user["id"]):
        raise ApiError(409, "hold_inactive", "Утримання вже неактивне.")
    return jsonify({"ok": True, "data": {"released": True}})


@bp.get("/bookings")
def bookings_endpoint():
    user = _current_user()
    bookings = database.get_user_bookings(user["id"])
    return jsonify(
        {
            "ok": True,
            "data": {
                "items": [_booking_json(item, user["id"]) for item in bookings],
            },
        }
    )


@bp.get("/bookings/<int:booking_id>")
def booking_endpoint(booking_id: int):
    user = _current_user()
    booking = database.get_booking(booking_id)
    if booking is None:
        raise ApiError(404, "not_found", "Заявку не знайдено.")
    if booking.get("user_id") != user["id"] and not config.is_admin(user["id"]):
        raise ApiError(404, "not_found", "Заявку не знайдено.")
    return jsonify(
        {
            "ok": True,
            "data": {
                "booking": _booking_json(
                    booking,
                    user["id"],
                    admin=config.is_admin(user["id"]),
                )
            },
        }
    )


@bp.delete("/bookings/<int:booking_id>")
def cancel_booking_endpoint(booking_id: int):
    user = _current_user()
    updated = database.cancel_user_booking(booking_id, user["id"])
    if updated is None:
        current = database.get_booking(booking_id)
        if current is None or current.get("user_id") != user["id"]:
            raise ApiError(404, "not_found", "Запис не знайдено.")
        if current.get("status") == database.STATUS_CANCELLED:
            return jsonify(
                {"ok": True, "data": {"booking": _booking_json(current, user["id"])}}
            )
        raise ApiError(
            409,
            "cancel_unavailable",
            "Запис уже не можна скасувати онлайн.",
        )
    telegram_api.notify_admin_cancelled(updated)
    return jsonify(
        {"ok": True, "data": {"booking": _booking_json(updated, user["id"])}}
    )


@bp.get("/admin/bookings")
def admin_bookings_endpoint():
    _current_admin()
    status = request.args.get("status", "pending").strip()
    if status == "all":
        db_status = None
    elif status in REQUEST_STATUSES:
        db_status = status
    else:
        raise ApiError(400, "invalid_status", "Некоректний фільтр статусу.")
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError as exc:
        raise ApiError(400, "invalid_page", "Некоректна сторінка.") from exc
    limit = 10
    total = database.count_bookings(db_status)
    pages = max(1, math.ceil(total / limit))
    page = min(page, pages)
    rows = database.get_bookings(
        db_status,
        limit=limit,
        offset=(page - 1) * limit,
    )
    return jsonify(
        {
            "ok": True,
            "data": {
                "items": [_booking_json(row, 0, admin=True) for row in rows],
                "total": total,
                "page": page,
                "pages": pages,
                "status": status,
            },
        }
    )


@bp.get("/admin/day")
def admin_day_endpoint():
    _current_admin()
    date_id = request.args.get("date", "").strip()
    try:
        date.fromisoformat(date_id)
    except ValueError as exc:
        raise ApiError(400, "invalid_date", "Некоректна дата.") from exc
    rows = database.get_bookings_for_date(date_id)
    return jsonify(
        {
            "ok": True,
            "data": {
                "date": _date_payload(date_id),
                "bookings": [_booking_json(row, 0, admin=True) for row in rows],
            },
        }
    )


def _admin_action(booking_id: int, target: str) -> dict:
    _current_admin()
    current = database.get_booking(booking_id)
    if current is None:
        raise ApiError(404, "not_found", "Заявку не знайдено.")
    if current.get("status") == target:
        return current
    if current.get("status") != database.STATUS_PENDING:
        raise ApiError(409, "already_processed", "Заявку вже оброблено.")
    if target == database.STATUS_CONFIRMED:
        changed = database.confirm_booking(booking_id)
    else:
        changed = database.reject_booking(booking_id)
    if not changed:
        raise ApiError(409, "already_processed", "Заявку вже оброблено.")
    updated = database.get_booking(booking_id)
    if updated is None:
        raise ApiError(500, "internal_error", "Не вдалося оновити заявку.")
    telegram_api.notify_client_status(updated, target)
    return updated


@bp.post("/admin/bookings/<int:booking_id>/confirm")
def admin_confirm_endpoint(booking_id: int):
    updated = _admin_action(booking_id, database.STATUS_CONFIRMED)
    return jsonify(
        {"ok": True, "data": {"booking": _booking_json(updated, 0, admin=True)}}
    )


@bp.post("/admin/bookings/<int:booking_id>/reject")
def admin_reject_endpoint(booking_id: int):
    updated = _admin_action(booking_id, database.STATUS_REJECTED)
    return jsonify(
        {"ok": True, "data": {"booking": _booking_json(updated, 0, admin=True)}}
    )
