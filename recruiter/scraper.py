"""Intercepts Spectrum's /api/spectrum/lobby/presences JSON response and
upserts the user list into the DB. Replaces the earlier DOM-based scraper.

Spectrum is a React SPA; when it opens a lobby, it fires a single REST call
that returns the complete presence list with rich metadata (badges, isGM,
presence.status, presence.info). That's everything we need — no scrolling,
no virtualized-list handling, no CSS selectors.
"""
import time
from playwright.sync_api import BrowserContext
from . import db

PRESENCES_PATH = "/api/spectrum/lobby/presences"
IDENTIFY_PATH = "/api/spectrum/auth/identify"


class NotLoggedInError(Exception):
    """Raised when Spectrum's identify response shows no authenticated member."""

# isGM=true already flags official CIG/moderator accounts. These badge names are
# additional staff signals we treat as off-limits for recruiting.
STAFF_BADGES = {"Developer", "Moderator", "QA", "CIG", "Community Manager"}

# presence.status values that count as "online" for filtering purposes.
ACTIVE_STATUSES = {"online", "playing", "do_not_disturb"}


def classify_member(member: dict) -> str:
    """Return STAFF | CIVILIAN | BACKER based on the badge/isGM data."""
    if member.get("isGM"):
        return "STAFF"
    badge_names = {(b.get("name") or "") for b in (member.get("meta") or {}).get("badges", [])}
    if badge_names & STAFF_BADGES:
        return "STAFF"
    if "Civilian" in badge_names:
        return "CIVILIAN"
    return "BACKER"


def profile_url(member: dict) -> str:
    handle = member.get("nickname") or member.get("displayname") or ""
    return f"https://robertsspaceindustries.com/citizens/{handle}"


def _identify_has_session(body) -> bool:
    """True if the identify response indicates an authenticated user."""
    if not isinstance(body, dict):
        return False
    data = body.get("data") or {}
    member = data.get("member") or {}
    return bool(member.get("id") or member.get("nickname"))


def scrape_lobby(context: BrowserContext, lobby_url: str, lobby_id: int | None) -> dict:
    """Open the lobby, capture the largest presences JSON payload, upsert users.

    Raises NotLoggedInError if the session is missing/expired."""
    page = context.new_page()
    captured: dict = {"data": [], "size": 0}
    auth_state: dict = {"logged_in": None}  # None = unknown, True/False once seen

    def on_response(resp):
        if IDENTIFY_PATH in resp.url and auth_state["logged_in"] is None:
            try:
                auth_state["logged_in"] = _identify_has_session(resp.json())
            except Exception:
                auth_state["logged_in"] = False
            return
        if PRESENCES_PATH not in resp.url:
            return
        try:
            body = resp.json()
        except Exception:
            return
        if not (isinstance(body, dict) and body.get("success") and isinstance(body.get("data"), list)):
            return
        # Spectrum may send incremental presence updates (small payloads) as
        # well as the initial full list. Keep the largest we've seen so we
        # end up with the complete roster.
        if len(body["data"]) > captured["size"]:
            captured["data"] = body["data"]
            captured["size"] = len(body["data"])

    page.on("response", on_response)

    try:
        page.goto(lobby_url, wait_until="domcontentloaded", timeout=45000)
        deadline = time.time() + 20
        # Wait for at least one non-empty capture. Keep waiting briefly after
        # the first hit in case a larger full payload arrives right after.
        while time.time() < deadline and captured["size"] == 0:
            page.wait_for_timeout(500)
        if captured["size"] > 0:
            page.wait_for_timeout(2000)  # grace window for the full payload

        if captured["size"] == 0 and auth_state["logged_in"] is False:
            raise NotLoggedInError(
                "Spectrum returned no authenticated session. Open the browser "
                "from the dashboard and log in to RSI, then try again."
            )

        data = captured["data"]
        by_group = {"STAFF": 0, "CIVILIAN": 0, "BACKER": 0}
        by_status: dict = {}

        for m in data:
            name = (m.get("nickname") or m.get("displayname") or "").strip()
            if not name:
                continue
            presence = m.get("presence") or {}
            tier = classify_member(m)
            by_group[tier] = by_group.get(tier, 0) + 1
            status = presence.get("status")
            by_status[status] = by_status.get(status, 0) + 1

            db.upsert_recruit(
                username=name,
                profile_url=profile_url(m),
                group_tier=tier,
                status=status,
                substatus=presence.get("info"),
                lobby_id=lobby_id,
            )

        return {
            "total": len(data),
            "by_group": by_group,
            "by_status": by_status,
        }
    finally:
        page.close()
