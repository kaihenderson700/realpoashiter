"""
mythicaljay-peace-watch (web service version)
-----------------------------------------------
Runs as a Render Web Service. A background thread checks the
gge-tracker.com API every 5 minutes for player `peace_disabled_at`.
If it's empty (still in peace), sends a Discord webhook alert.

A tiny Flask endpoint ("/") is exposed just so Render sees an open
port and considers the service healthy; it also shows the last check
result.
"""

import os
import sys
import threading
import time
from datetime import datetime, timezone

import requests
from flask import Flask

API_BASE = "https://api.gge-tracker.com/api/v1"

PLAYER_NAME = "mythicaljay"
SERVER = "US1"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1416915562621173891/jwqMhksUhzp3s4oyqBp44CmsNLL9Uhahkw7z6-Yet7htvJoCFggrkZwKXY4oQhGUxAIF"
DISCORD_MESSAGE = "hey <@701463248830070805> jay bird gone"
REQUEST_TIMEOUT = 15
CHECK_INTERVAL_SECONDS = 5 * 60  # 5 minutes

app = Flask(__name__)
status = {"last_checked": None, "peace_disabled_at": None, "last_error": None}


def get_player(player_name: str, server: str) -> dict:
    url = f"{API_BASE}/players/{player_name}"
    headers = {"gge-server": server}
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def send_discord_alert(webhook_url: str, message: str) -> None:
    resp = requests.post(webhook_url, json={"content": message}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()


def check_once() -> None:
    try:
        player = get_player(PLAYER_NAME, SERVER)
        peace_disabled_at = player.get("peace_disabled_at")
        status["peace_disabled_at"] = peace_disabled_at
        status["last_error"] = None
        print(f"Checked '{PLAYER_NAME}' on {SERVER}: peace_disabled_at={peace_disabled_at!r}")

        if not peace_disabled_at:
            send_discord_alert(DISCORD_WEBHOOK_URL, DISCORD_MESSAGE)
            print("Discord alert sent (peace_disabled_at is empty).")
    except requests.RequestException as e:
        status["last_error"] = str(e)
        print(f"ERROR: {e}", file=sys.stderr)
    finally:
        status["last_checked"] = datetime.now(timezone.utc).isoformat()


def background_loop() -> None:
    while True:
        check_once()
        time.sleep(CHECK_INTERVAL_SECONDS)


@app.route("/")
def index():
    return status


if __name__ == "__main__":
    threading.Thread(target=background_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
