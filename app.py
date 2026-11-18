import logging
import os

import psycopg2
from flask import Flask, jsonify

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("demo-app")

app = Flask(__name__)


def db_connect():
    # All settings come from env vars, injected from a Kubernetes Secret.
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
    )


CONFIG_DIR = os.getenv("CONFIG_DIR", "/etc/demo-app")


def read_config():
    """Return {filename: content} for every file in CONFIG_DIR (a mounted ConfigMap).

    Read on each request: when a ConfigMap volume is updated, the files change
    in place after a short delay, without restarting the pod.
    """
    config = {}
    if os.path.isdir(CONFIG_DIR):
        for name in sorted(os.listdir(CONFIG_DIR)):
            path = os.path.join(CONFIG_DIR, name)
            # Skip the ..data / ..timestamp entries Kubernetes uses for atomic updates.
            if name.startswith("..") or not os.path.isfile(path):
                continue
            with open(path) as f:
                config[name] = f.read().strip()
    return config


@app.get("/config")
def config():
    """Shows the files mounted from the ConfigMap."""
    cfg = read_config()
    if not cfg:
        log.warning("No config files found in %s", CONFIG_DIR)
    return jsonify(config_dir=CONFIG_DIR, files=cfg)


@app.get("/healthz")
def healthz():
    """Liveness: the process is up. Does not touch the DB."""
    return jsonify(status="ok")


@app.get("/readyz")
def readyz():
    """Readiness: the app can reach its database."""
    try:
        with db_connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify(status="ready")
    except Exception as e:
        log.error("DB check failed: %s", e)
        return jsonify(status="db unavailable"), 503


@app.get("/")
def index():
    try:
        with db_connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
        log.debug("Queried DB version: %s", version)
        message = read_config().get("greeting", "Hello from Kubernetes!")
        return jsonify(message=message, db_version=version)
    except Exception as e:
        log.error("DB query failed: %s", e)
        return jsonify(error="db unavailable"), 503


if __name__ == "__main__":
    log.info("Starting demo-app (log level %s)", LOG_LEVEL)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
