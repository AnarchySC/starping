"""Optional credential storage via the OS keyring.

Stored credentials are used only to auto-type into the RSI login form inside the
Playwright browser. They are never logged, echoed, or written to disk in plaintext.
The preferred flow is to skip credentials entirely and rely on the persistent
browser session in data/browser/.
"""
import keyring

SERVICE = "sc-recruiter"
USER_KEY = "rsi_username"


def save_credentials(username: str, password: str) -> None:
    keyring.set_password(SERVICE, USER_KEY, username)
    keyring.set_password(SERVICE, username, password)


def get_credentials() -> tuple[str, str] | None:
    username = keyring.get_password(SERVICE, USER_KEY)
    if not username:
        return None
    password = keyring.get_password(SERVICE, username)
    if not password:
        return None
    return username, password


def clear_credentials() -> None:
    username = keyring.get_password(SERVICE, USER_KEY)
    if username:
        try:
            keyring.delete_password(SERVICE, username)
        except keyring.errors.PasswordDeleteError:
            pass
    try:
        keyring.delete_password(SERVICE, USER_KEY)
    except keyring.errors.PasswordDeleteError:
        pass
