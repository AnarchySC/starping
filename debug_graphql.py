"""Capture all GraphQL traffic during a lobby load, identify the presence query."""
import json
import sys
from pathlib import Path
from recruiter import browser

LOBBY_URL = sys.argv[1] if len(sys.argv) > 1 else "https://robertsspaceindustries.com/spectrum/community/SC/lobby/1"
OUT_DIR = Path("/tmp/spectrum_gql")


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for f in OUT_DIR.glob("*.json"):
        f.unlink()

    captured = []

    with browser.launch(headless=False) as ctx:
        page = ctx.new_page()

        def on_response(resp):
            url = resp.url
            if "graphql" not in url.lower() and "/api/" not in url.lower():
                return
            try:
                body_text = resp.text()
            except Exception:
                return
            try:
                body = json.loads(body_text)
            except Exception:
                return

            # Extract operation name from request post data
            op = "?"
            try:
                req = resp.request
                if req.method == "POST" and req.post_data:
                    pd = json.loads(req.post_data)
                    if isinstance(pd, list) and pd:
                        op = pd[0].get("operationName", "?")
                    elif isinstance(pd, dict):
                        op = pd.get("operationName", "?")
            except Exception:
                pass

            blob = json.dumps(body).lower()
            interesting_tokens = ["presence", "member", "online", "nickname", "citizen"]
            hits = [t for t in interesting_tokens if t in blob]

            rec = {
                "url": url,
                "status": resp.status,
                "operation": op,
                "hits": hits,
                "size": len(body_text),
            }
            captured.append(rec)

            # Save every response to disk for inspection
            idx = len(captured)
            fname = f"{idx:03d}_{op}_{'-'.join(hits) or 'no-hit'}.json"
            (OUT_DIR / fname).write_text(body_text)

        page.on("response", on_response)

        print(f"Navigating to {LOBBY_URL}")
        page.goto(LOBBY_URL, wait_until="domcontentloaded", timeout=45000)
        print("Waiting 12s for GraphQL to settle...")
        page.wait_for_timeout(12000)

        print(f"\n=== Captured {len(captured)} network responses (GraphQL/API) ===")
        interesting = [r for r in captured if r["hits"]]
        print(f"Of those, {len(interesting)} contain presence/member/online/nickname/citizen tokens.\n")

        for r in interesting:
            print(f"  [{r['operation']}] {r['hits']}  {r['size']}B  {r['url'][:80]}")

        print(f"\nAll response bodies saved to {OUT_DIR}")
        print("Browser closing in 3s.")
        page.wait_for_timeout(3000)


if __name__ == "__main__":
    main()
