# StarPing — by AnarchyGames.org

Local tool for org recruiters. Scrapes the Online Users panel of a Spectrum lobby, lets you filter by group (STAFF / CIVILIAN / BACKER) and online/away status, queues targets, and sends a templated DM when you push the Send button for a recruit.

## Design notes

- **Manual push only.** No auto-cadence, no batching. Every DM is a button click, one at a time.
- **STAFF is off by default** on the queue filter (DMing CIG staff is a fast way to get banned).
- **Persistent Playwright browser** — first launch opens a visible Chromium, you log in once, session persists in `data/browser/`.
- **Optional credential storage** via the OS keyring (never plaintext) for auto-relogin if the session expires.
- **No CAPTCHA bypass, no proxy rotation, no fingerprint spoofing.** If Spectrum challenges, the visible browser surfaces it and you solve it yourself.

## Setup

```bash
cd ~/Documents/Projects/sc-recruiter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
./run.sh
# then open http://localhost:5050
# (override with SC_RECRUITER_PORT=xxxx if 5050 is taken)
```

First time: click "Open browser & log in" on the dashboard, log into RSI in the Chromium window that opens, close it. Session is now saved.

## Workflow

1. **Dashboard** → add a lobby URL (right-click a Spectrum lobby in your browser, copy link).
2. **Scrape** → pick lobby, click "Scrape online users". Playwright opens lobby, reads the online users panel, writes results to the queue.
3. **Queue** → filter by group / status, uncheck anyone you don't want, the unchecked stay but won't be sent to.
4. **Compose** → write the message template. Variables: `{{username}}`, `{{group}}`, `{{lobby}}`.
5. **Send** → per row, click "Send". Playwright opens the DM, fills it, sends, records result.

## Known tuning points

Spectrum's DOM may change. Selectors live in `recruiter/scraper.py` and `recruiter/sender.py` under a `SELECTORS` dict at the top — update there if Spectrum ships a redesign.

## Building the Windows installer

Two paths:

**Local (Windows VM, fast iteration)**
```powershell
# One-time: install Python 3.12+ and Inno Setup 6
choco install python innosetup

# On every build:
.\build.ps1 -Version 0.1.0
# Output: dist\StarPing-Setup.exe
```

**CI (release-quality)**
```bash
git tag v0.1.0
git push origin v0.1.0
```
The `.github/workflows/build.yml` workflow runs on `windows-latest`, produces `StarPing-Setup.exe`, and attaches it to a draft GitHub release.

