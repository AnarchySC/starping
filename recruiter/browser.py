from contextlib import contextmanager
from playwright.sync_api import sync_playwright, BrowserContext

from . import paths

SPECTRUM_URL = "https://robertsspaceindustries.com/spectrum/community/SC"
RSI_LOGIN_URL = "https://robertsspaceindustries.com/connect?jumpto=/spectrum/community/SC"


@contextmanager
def launch(headless: bool = False, slow_mo: int = 0):
    """Launch persistent Chromium context so session cookies survive between runs."""
    user_data_dir = paths.browser_profile_dir()
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=headless,
            slow_mo=slow_mo,
            viewport={"width": 1400, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            yield context
        finally:
            context.close()


def is_logged_in(context: BrowserContext) -> bool:
    """Quick session probe: navigate to spectrum and check for an auth indicator."""
    page = context.new_page()
    try:
        page.goto(SPECTRUM_URL, wait_until="domcontentloaded", timeout=30000)
        # Logged-in users see their avatar/profile link in the header.
        # Logged-out users see a "Sign In" button.
        sign_in = page.locator("text=/sign in/i").first
        try:
            sign_in.wait_for(state="visible", timeout=3000)
            return False
        except Exception:
            return True
    finally:
        page.close()


def open_for_login() -> None:
    """Open headful browser to the RSI login page. User logs in manually, then closes it."""
    with launch(headless=False) as context:
        page = context.new_page()
        page.goto(RSI_LOGIN_URL, wait_until="domcontentloaded")
        # Wait until the user navigates away from the login page (i.e. they finished logging in)
        # or closes the window. We poll up to 10 minutes.
        try:
            page.wait_for_url(
                lambda url: "connect" not in url and "login" not in url.lower(),
                timeout=600_000,
            )
        except Exception:
            # Timeout or page closed — either way, we're done.
            pass
