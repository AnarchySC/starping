"""Sends a DM to a single recruit via the Spectrum UI.

One function call = one DM. Caller (Flask route) drives cadence by only invoking
on a button click. No internal batching.
"""
import time
from playwright.sync_api import BrowserContext, TimeoutError as PWTimeout

SELECTORS = {
    # From a citizen profile page, button that opens the DM composer
    "open_dm_button": 'button:has-text("Send Message"), a:has-text("Send Message"), button:has-text("Message")',
    # DM textarea / contenteditable
    "dm_input": '[contenteditable="true"][class*="message"], textarea[placeholder*="message" i], div[role="textbox"]',
    # Send button inside the DM composer
    "dm_send": 'button:has-text("Send"):not(:has-text("Message"))',
    # CAPTCHA / challenge indicator
    "captcha": 'iframe[src*="hcaptcha"], iframe[src*="recaptcha"], :text("verify you are human")',
    # Rate limit message
    "rate_limit": ':text("too many"), :text("rate limit"), :text("try again later")',
}


class SendResult:
    SENT = "sent"
    NO_PROFILE = "no_profile_url"
    NO_DM_BUTTON = "no_dm_button"
    NO_INPUT = "no_input_field"
    CAPTCHA = "captcha_challenged"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


def render_message(template: str, recruit_row) -> str:
    return (
        template
        .replace("{{username}}", recruit_row["username"] or "")
        .replace("{{group}}", recruit_row["group_tier"] or "")
        .replace("{{lobby}}", recruit_row["lobby_name"] if "lobby_name" in recruit_row.keys() else "")
    )


def send_dm(context: BrowserContext, recruit_row, message: str) -> tuple[str, str | None]:
    """Return (result, error_message)."""
    profile_url = recruit_row["profile_url"]
    if not profile_url:
        # Fall back to the citizens search URL
        username = recruit_row["username"]
        if not username:
            return SendResult.NO_PROFILE, "no username"
        profile_url = f"https://robertsspaceindustries.com/citizens/{username}"

    page = context.new_page()
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        # Detect CAPTCHA or rate limit on the profile page itself
        if page.locator(SELECTORS["captcha"]).count() > 0:
            return SendResult.CAPTCHA, "captcha on profile"
        if page.locator(SELECTORS["rate_limit"]).count() > 0:
            return SendResult.RATE_LIMITED, None

        # Find and click the "Send Message" button
        dm_btn = page.locator(SELECTORS["open_dm_button"]).first
        try:
            dm_btn.wait_for(state="visible", timeout=8000)
        except PWTimeout:
            return SendResult.NO_DM_BUTTON, f"no DM button on {profile_url}"
        dm_btn.click()
        page.wait_for_timeout(1500)

        # Check for CAPTCHA in the composer
        if page.locator(SELECTORS["captcha"]).count() > 0:
            return SendResult.CAPTCHA, "captcha in composer"

        # Fill the message
        dm_input = page.locator(SELECTORS["dm_input"]).first
        try:
            dm_input.wait_for(state="visible", timeout=5000)
        except PWTimeout:
            return SendResult.NO_INPUT, "DM input never appeared"

        dm_input.click()
        # Use type() with small per-char delay so it looks human, not paste-dumped
        dm_input.type(message, delay=25)
        page.wait_for_timeout(500)

        # Click send
        send_btn = page.locator(SELECTORS["dm_send"]).first
        try:
            send_btn.wait_for(state="visible", timeout=3000)
        except PWTimeout:
            # Try Enter key as fallback
            dm_input.press("Enter")
        else:
            send_btn.click()

        page.wait_for_timeout(1500)

        # Final check for CAPTCHA / rate limit popping up after send
        if page.locator(SELECTORS["captcha"]).count() > 0:
            return SendResult.CAPTCHA, "captcha after send"
        if page.locator(SELECTORS["rate_limit"]).count() > 0:
            return SendResult.RATE_LIMITED, None

        return SendResult.SENT, None

    except Exception as e:
        return SendResult.ERROR, str(e)
    finally:
        page.close()
