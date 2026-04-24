"""Find the Spectrum API endpoint that returns the list of chat lobbies."""
import json
from pathlib import Path
from recruiter import browser

OUT_DIR = Path("/tmp/spectrum_lobbies")
HOME_URL = "https://robertsspaceindustries.com/spectrum/community/SC"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for f in OUT_DIR.glob("*.json"):
        f.unlink()

    captured = []
    with browser.launch(headless=False) as ctx:
        page = ctx.new_page()

        def on_response(resp):
            url = resp.url
            if "/api/" not in url.lower():
                return
            try:
                body_text = resp.text()
                body = json.loads(body_text)
            except Exception:
                return
            blob = body_text.lower()
            tokens = ["lobby", "lobbies", "general", "recruitment", "helpdesk", "subscribers"]
            hits = [t for t in tokens if t in blob]
            rec = {"url": url, "status": resp.status, "hits": hits, "size": len(body_text)}
            captured.append(rec)
            idx = len(captured)
            (OUT_DIR / f"{idx:03d}_{'-'.join(hits) or 'no-hit'}.json").write_text(body_text)

        page.on("response", on_response)
        page.goto(HOME_URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(10000)

        print(f"Captured {len(captured)} /api/ responses")
        for r in sorted(captured, key=lambda x: -len(x["hits"])):
            if r["hits"]:
                print(f"  {r['size']:>8}B  hits={r['hits']}  {r['url'][:90]}")
        print(f"\nSaved to {OUT_DIR}")
        page.wait_for_timeout(2000)


if __name__ == "__main__":
    main()
