"""Diagnostic: open a lobby and report what the Online Users panel actually looks like.

Prints the outer HTML of candidate containers and a sample of user rows so we can
pick real selectors.
"""
import sys
from recruiter import browser

LOBBY_URL = sys.argv[1] if len(sys.argv) > 1 else "https://robertsspaceindustries.com/spectrum/community/SC/lobby/1"


def main():
    with browser.launch(headless=False) as ctx:
        page = ctx.new_page()
        print(f"Navigating to {LOBBY_URL}")
        page.goto(LOBBY_URL, wait_until="domcontentloaded", timeout=45000)
        print("Waiting 6s for React/Ember hydration...")
        page.wait_for_timeout(6000)

        print("\n=== Page title ===")
        print(page.title())

        print("\n=== Any text containing 'ONLINE USERS' visible? ===")
        try:
            loc = page.get_by_text("ONLINE USERS", exact=False).first
            print("  yes — visible =", loc.is_visible())
            # Walk up to find the container
            html = loc.evaluate("el => { let n = el; for (let i=0; i<5; i++) { n = n.parentElement; if (!n) break; } return n ? n.outerHTML.slice(0, 2000) : 'no parent'; }")
            print("\n=== HTML of ancestor (5 levels up) ===")
            print(html)
        except Exception as e:
            print(f"  no — {e}")

        print("\n=== Candidate selector probe ===")
        probes = [
            '[class*="online"]',
            '[class*="lobby-members"]',
            '[class*="members-panel"]',
            '[class*="presence"]',
            'aside',
            '[class*="nickname"]',
            '[class*="username"]',
            'a[href*="/citizens/"]',
            '[class*="member-item"]',
            '[class*="user-row"]',
        ]
        for sel in probes:
            try:
                n = page.locator(sel).count()
                print(f"  {sel}: {n} matches")
            except Exception as e:
                print(f"  {sel}: ERROR {e}")

        print("\n=== First 3 citizen links ===")
        links = page.locator('a[href*="/citizens/"]')
        n = min(links.count(), 3)
        for i in range(n):
            href = links.nth(i).get_attribute("href")
            text = links.nth(i).inner_text()[:60]
            print(f"  {href}  :: {text!r}")

        print("\n=== Saving screenshot to /tmp/spectrum_debug.png ===")
        page.screenshot(path="/tmp/spectrum_debug.png", full_page=True)

        print("\n=== Saving full HTML to /tmp/spectrum_debug.html ===")
        with open("/tmp/spectrum_debug.html", "w") as f:
            f.write(page.content())

        print("\nBrowser will close in 3s.")
        page.wait_for_timeout(3000)


if __name__ == "__main__":
    main()
