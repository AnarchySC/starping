"""Deep scrape diagnostic: capture EVERY /lobby/presences response (request body + response)
so we can tell whether Spectrum paginates, what params are used, and how many users we actually see."""
import json
import sys
import time
from pathlib import Path
from recruiter import browser

LOBBY_URL = sys.argv[1] if len(sys.argv) > 1 else "https://robertsspaceindustries.com/spectrum/community/SC/lobby/1"
OUT = Path("/tmp/spectrum_scrape_deep")


def main():
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*"):
        f.unlink()
    captured = []

    with browser.launch(headless=False) as ctx:
        page = ctx.new_page()

        def on_response(resp):
            if "/api/spectrum/lobby/presences" not in resp.url:
                return
            try:
                req_body = resp.request.post_data or "(no body)"
                body_text = resp.text()
                body = json.loads(body_text)
            except Exception as e:
                return
            n = len(body.get("data", [])) if isinstance(body.get("data"), list) else 0
            captured.append({
                "url": resp.url,
                "method": resp.request.method,
                "request_body": req_body,
                "response_count": n,
                "response_size": len(body_text),
            })
            idx = len(captured)
            (OUT / f"{idx:03d}_resp.json").write_text(body_text)
            (OUT / f"{idx:03d}_req.txt").write_text(f"{resp.request.method} {resp.url}\n\n{req_body}")

        page.on("response", on_response)
        page.goto(LOBBY_URL, wait_until="domcontentloaded", timeout=45000)
        # Wait long enough for all paginated calls to land
        page.wait_for_timeout(15000)

        # Also scroll the online panel to trigger any lazy-load
        try:
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(2000)
        except Exception:
            pass

        print(f"\nCaptured {len(captured)} presences requests:")
        for i, c in enumerate(captured, 1):
            print(f"  [{i}] {c['method']} → {c['response_count']} users ({c['response_size']}B)")
            print(f"      req_body: {c['request_body'][:200]}")
        print(f"\nTotal unique users across all pages (by nickname):")
        all_names = set()
        for f in sorted(OUT.glob("*_resp.json")):
            d = json.loads(f.read_text())
            for m in d.get("data", []):
                nm = m.get("nickname") or m.get("displayname")
                if nm: all_names.add(nm)
        print(f"  {len(all_names)} unique users")
        page.wait_for_timeout(2000)


if __name__ == "__main__":
    main()
