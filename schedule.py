from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import (
    BOOKING_DAYS_AHEAD,
    BREAKS,
    CANCELLATION_CUTOFF_MINUTES,
    SLOT_STEP_MINUTES,
    TIMEZONE,
    WORKING_HOURS_BY_WEEKDAY,
)

MONTHS_UK = (
    "січня",
    "лютого",
    "березня",
    "квітня",
    "травня",
    "червня",
    "липня",
    "серпня",
    "вересня",
    "жовтня",
    "листопада",
    "грудня",
)

# Старі демо-слоти, які могли залишитися в уже створеній базі.
LEGACY_TIME_IDS = {
    "t1": "10:00",
    "t2": "12:00",
    "t3": "14:00",
    "t4": "16:00",
    "t5": "18:00",
}


def parse_clock(value: str) -> int | None:
    try:
        hours, minutes = value.split(":", 1)
        result = int(hours) * 60 + int(minutes)
    except (AttributeError, TypeError, ValueError):
        return None
    if not (0 <= result < 24 * 60):
        return None
    return result


def format_clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def time_to_minutes(time_id: str) -> int | None:
    if time_id in LEGACY_TIME_IDS:
        return parse_clock(LEGACY_TIME_IDS[time_id])
    return parse_clock(time_id)


def overlaps(
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int,
) -> bool:
    return first_start < second_end and second_start < first_end


def _window(date_id: str) -> tuple[int, int] | None:
    try:
        day = date.fromisoformat(date_id)
    except ValueError:
        return None
    hours = WORKING_HOURS_BY_WEEKDAY.get(day.weekday())
    if hours is None:
        return None
    start = parse_clock(hours[0])
    end = parse_clock(hours[1])
    if start is None or end is None or start >= end:
        return None
    return start, end


def is_working_date(date_id: str) -> bool:
    return _window(date_id) is not None


def is_within_booking_window(
    date_id: str,
    now: datetime | None = None,
    days: int = BOOKING_DAYS_AHEAD,
) -> bool:
    try:
        day = date.fromisoformat(date_id)
    except ValueError:
        return False
    current = (now or _date_now()).date()
    return current <= day < current + timedelta(days=days)


def date_label(date_id: str) -> str:
    try:
        day = date.fromisoformat(date_id)
    except ValueError:
        return date_id
    return f"{day.day} {MONTHS_UK[day.month - 1]}"


def _zone():
    try:
        return ZoneInfo(TIMEZONE)
    except ZoneInfoNotFoundError:
        return timezone.utc


def _date_now() -> datetime:
    return datetime.now(_zone())


def available_slots(
    date_id: str,
    service: dict,
    occupied: list[tuple[int, int]] | None = None,
    now: datetime | None = None,
) -> list[tuple[str, str]]:
    window = _window(date_id)
    if window is None:
        return []
    duration = int(service.get("duration_minutes", 60))
    if duration <= 0:
        return []
    opening, closing = window
    current = now or _date_now()
    try:
        day = date.fromisoformat(date_id)
    except ValueError:
        return []

    slots: list[tuple[str, str]] = []
    start = opening
    while start + duration <= closing:
        end = start + duration
        if not any(overlaps(start, end, break_start, break_end) for break_start, break_end in BREAKS):
            start_at = datetime.combine(day, time(hour=start // 60, minute=start % 60), tzinfo=_zone())
            if start_at > current and not any(
                overlaps(start, end, occupied_start, occupied_end)
                for occupied_start, occupied_end in (occupied or [])
            ):
                label = format_clock(start)
                slots.append((label, label))
        start += SLOT_STEP_MINUTES
    return slots


def available_dates(
    service: dict,
    occupied_lookup=None,
    today: date | None = None,
    now: datetime | None = None,
    days: int = BOOKING_DAYS_AHEAD,
) -> list[tuple[str, str]]:
    current = now or _date_now()
    current_date = today or current.date()
    result: list[tuple[str, str]] = []
    for offset in range(days):
        day = current_date + timedelta(days=offset)
        date_id = day.isoformat()
        if _window(date_id) is None:
            continue
        occupied = occupied_lookup(date_id) if occupied_lookup is not None else []
        if available_slots(date_id, service, occupied, now=current):
            result.append((date_id, date_label(date_id)))
    return result


def appointment_start(booking: dict) -> datetime | None:
    try:
        day = date.fromisoformat(booking["date_id"])
    except (KeyError, ValueError):
        return None
    minutes = time_to_minutes(str(booking.get("time_id", "")))
    if minutes is None:
        return None
    return datetime.combine(
        day,
        time(hour=minutes // 60, minute=minutes % 60),
        tzinfo=_zone(),
    )


def can_cancel(booking: dict, now: datetime | None = None) -> bool:
    if booking.get("status") not in {"pending", "confirmed"}:
        return False
    start = appointment_start(booking)
    if start is None:
        return False
    current = now or _date_now()
    return start - current >= timedelta(minutes=CANCELLATION_CUTOFF_MINUTES)
