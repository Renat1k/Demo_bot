import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from config import PORT
from mini_app_api import bp as api_bp

logger = logging.getLogger(__name__)

WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.register_blueprint(api_bp)


@app.get("/health")
def health():
    return "ok", 200


@app.get("/")
@app.get("/app")
@app.get("/app/")
def mini_app_index():
    return send_from_directory(WEBAPP_DIR, "index.html", max_age=0)


@app.get("/app/<path:filename>")
def mini_app_asset(filename: str):
    return send_from_directory(WEBAPP_DIR, filename, max_age=0)


@app.after_request
def security_headers(response):
    if request.path == "/" or request.path.startswith("/app"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://telegram.org; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' https://telegram.org https://*.telegram.org; "
            "frame-ancestors https://web.telegram.org https://*.telegram.org; "
            "base-uri 'none'; form-action 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(Exception)
def unhandled_error(error):
    if isinstance(error, HTTPException):
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": {
                            "code": "http_error",
                            "message": error.description,
                        },
                    }
                ),
                error.code or 500,
            )
        return error
    logger.exception("Необроблена помилка web-сервера")
    if request.path.startswith("/api/"):
        return (
            jsonify(
                {
                    "ok": False,
                    "error": {
                        "code": "internal_error",
                        "message": "Внутрішня помилка сервера.",
                    },
                }
            ),
            500,
        )
    return "Внутрішня помилка сервера.", 500


def run_health_server() -> None:
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
