from flask import Flask

from config import PORT

app = Flask(__name__)


@app.get("/")
@app.get("/health")
def health():
    return "ok", 200


def run_health_server() -> None:
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
