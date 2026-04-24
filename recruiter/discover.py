"""Discover all chat lobbies visible to the logged-in user.

Spectrum's /api/spectrum/auth/identify call returns the session bootstrap
including every community the user is in and every lobby within each.
"""
import time
from playwright.sync_api import BrowserContext

IDENTIFY_PATH = "/api/spectrum/auth/identify"
SPECTRUM_HOME = "https://robertsspaceindustries.com/spectrum/community/SC"
LOBBY_URL_TEMPLATE = "https://robertsspaceindustries.com/spectrum/community/SC/lobby/{id}"


class NotLoggedInError(Exception):
    pass


def discover_lobbies(context: BrowserContext) -> list[dict]:
    page = context.new_page()
    captured: list[dict] = []

    def on_response(resp):
        if IDENTIFY_PATH not in resp.url:
            return
        try:
            captured.append(resp.json())
        except Exception:
            return

    page.on("response", on_response)

    try:
        page.goto(SPECTRUM_HOME, wait_until="domcontentloaded", timeout=45000)
        deadline = time.time() + 15
        while time.time() < deadline and not captured:
            page.wait_for_timeout(500)
        if not captured:
            return []

        body = captured[0]
        data = body.get("data") or {}
        member = data.get("member") or {}
        if not (member.get("id") or member.get("nickname")):
            raise NotLoggedInError(
                "Spectrum returned no authenticated session. Log in to RSI first."
            )
        lobbies: list[dict] = []
        for c in data.get("communities", []):
            for l in c.get("lobbies") or []:
                lobbies.append({
                    "id": l["id"],
                    "name": f"#{l['name']}",
                    "url": LOBBY_URL_TEMPLATE.format(id=l["id"]),
                    "description": l.get("description") or "",
                    "online_count": l.get("online_members_count", 0),
                    "type": l.get("type"),
                })
        return lobbies
    finally:
        page.close()
