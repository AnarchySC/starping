<div align="center">

<img src="docs/banner.svg" alt="StarPing — by AnarchyGames.org" width="100%">

<br><br>

<a href="https://github.com/AnarchySC/starping/releases/latest">
  <img src="docs/download-now.svg" alt="Download Now — Windows Installer" width="340">
</a>

<br>

[![Build Windows Installer](https://github.com/AnarchySC/starping/actions/workflows/build.yml/badge.svg)](https://github.com/AnarchySC/starping/actions/workflows/build.yml)
![Platform](https://img.shields.io/badge/platform-Windows-00d4ff?style=flat-square)
![License](https://img.shields.io/badge/license-All%20rights%20reserved-6a7080?style=flat-square)
![Brand](https://img.shields.io/badge/by-AnarchyGames.org-E85D04?style=flat-square)

</div>

---

## What it is

**StarPing** is a local productivity tool for Star Citizen organization recruiters. It scrapes the Online Users panel of any Spectrum chat lobby, filters by group tier (STAFF / BACKER / CIVILIAN) and presence, and lets you send templated DMs one click at a time from a neon-dark web UI running on your own machine.

Built for humans, not bots. Manual push per message, human cadence, no CAPTCHA bypass, no proxy rotation, no fingerprint spoofing.

## Highlights

- **Live Spectrum scrape** via the Presences API — hundreds of users in one click
- **Group + status filters** — target only online BACKER/CIVILIAN, skip "In Menus"
- **Multi-template system** — save as many recruiting messages as you want, per-row dropdown picks which one to send
- **Bulk actions** — multi-select rows, assign a template to all of them at once
- **Lobby discovery** — one click finds every Spectrum chat lobby your account has access to
- **Persistent session** — log in to RSI once, the embedded Chromium remembers you

## Design philosophy

Automation should amplify the recruiter, not replace them. Every DM is a single button click. The tool buys speed, not scale — you still read every profile, still hit send every time. That distinction is what keeps accounts alive and communities un-spammed.

## Install

Grab the latest Windows installer from **[Releases](https://github.com/AnarchySC/starping/releases/latest)**. Double-click `StarPing-Setup.exe`, then launch StarPing from the Start Menu.

First run: click **Open browser & log in** on the Dashboard, sign in to RSI inside the embedded Chromium, close the window. You're ready.

## Run from source

```bash
git clone https://github.com/AnarchySC/starping.git
cd starping
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python app.py   # → http://localhost:5050
```

## Build the Windows installer

**Locally on a Windows machine:**
```powershell
choco install python innosetup
.\build.ps1 -Version 0.1.0
# Output: dist\StarPing-Setup.exe
```

**Via GitHub Actions:**
```bash
git tag v0.1.0
git push origin v0.1.0
# workflow attaches the installer to a draft release
```

## Workflow

1. **Dashboard** → click `Discover lobbies from Spectrum`. Every lobby you have access to gets added.
2. **Dashboard** → click `Scrape` on a lobby. Users are imported with group tier + presence status.
3. **Message** → save one or more templates. `{{username}}` / `{{group}}` / `{{lobby}}` variables available.
4. **Queue** → filter, multi-select, assign a template to the selected rows, then `Send` per row.

## Scope lines held

| | |
|---|---|
| CAPTCHA bypass | **No** — you solve them manually in the browser window |
| Proxy rotation | **No** |
| Fingerprint spoofing | **No** |
| Auto-cadence / scheduling | **No** — every send is a button click |
| STAFF DMing | **Off by default** in filters (`isGM: true` users are excluded) |

## License

All rights reserved. StarPing is published as source-viewable by AnarchyGames.org; see [LICENSE](LICENSE) when present.

---

<div align="center">

**StarPing · by [AnarchyGames.org](https://anarchygames.org)**

</div>
