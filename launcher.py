"""Frozen-exe entry point.

PyInstaller compiles this into StarPing.exe. On launch:
 - Initialize the DB (in the platform-aware data dir).
 - Start Flask in a background thread on localhost.
 - Open the default browser to the app.
 - Block until the user closes the window (console exit).

Runtime notes (Windows-packaged build):
 - Chromium is installed by the Inno Setup installer into %LOCALAPPDATA%\\ms-playwright\\,
   which is where Playwright looks by default.
 - User data (DB, logs, browser profile) lives in %APPDATA%\\StarPing\\.
"""
import os
import sys
import threading
import time
import webbrowser


def _port() -> int:
    return int(os.environ.get("STARPING_PORT", "5050"))


def _run_flask():
    # Imports are inside the function so PyInstaller picks them up but startup
    # is cheap if the launcher is invoked just to print help, etc.
    from app import app
    from recruiter import db

    db.init()
    app.run(host="127.0.0.1", port=_port(), debug=False, use_reloader=False, threaded=True)


def main() -> None:
    url = f"http://localhost:{_port()}"

    # Start Flask in the background; wait briefly for the socket to bind
    # before opening the browser.
    t = threading.Thread(target=_run_flask, daemon=True)
    t.start()
    time.sleep(1.5)

    print(f"\n  StarPing running at {url}")
    print("  Close this window to stop the app.\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        while t.is_alive():
            t.join(timeout=1.0)
    except KeyboardInterrupt:
        print("\nStopping.")
        sys.exit(0)


if __name__ == "__main__":
    main()
