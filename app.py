import logging
import os
import threading
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from recruiter import db, browser, scraper, sender, discover, paths


def _configure_logging() -> None:
    log_file = paths.logs_dir() / "starping.log"
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    # Clear pre-existing handlers (Flask may add its own)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
    root.setLevel(logging.INFO)


_configure_logging()

app = Flask(__name__)
app.secret_key = os.environ.get("STARPING_SECRET") or "local-only-not-secret"
app.logger.info("StarPing starting. data_dir=%s", paths.data_dir())

_browser_lock = threading.Lock()


def _run_with_browser(fn):
    """Run `fn(context)` inside a fresh persistent-context session. Serialized via lock
    so we never have two Playwright contexts on the same user-data-dir."""
    with _browser_lock:
        with browser.launch(headless=False) as ctx:
            return fn(ctx)


SEED_LOBBY_NAMES = [
    "Recruiting",
    "General Chatter",
    "Newcomer Forum",
    "Off-Topic",
    "Ask the Community",
]


@app.route("/")
def dashboard():
    lobbies = db.list_lobbies()
    template = db.get_active_template()
    recruits = db.list_recruits(only_unsent=False)
    stats = {
        "total": len(recruits),
        "sent": sum(1 for r in recruits if r["sent_at"]),
        "pending": sum(1 for r in recruits if not r["sent_at"]),
    }
    # Deduped suggestion list: previously-used names first, then seed defaults.
    used = {l["name"] for l in lobbies}
    name_suggestions = sorted(used) + [n for n in SEED_LOBBY_NAMES if n not in used]
    return render_template(
        "dashboard.html",
        lobbies=lobbies,
        template=template,
        stats=stats,
        name_suggestions=name_suggestions,
    )


@app.route("/login", methods=["POST"])
def login():
    def _open(ctx):
        page = ctx.new_page()
        page.goto(browser.RSI_LOGIN_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_url(
                lambda url: "connect" not in url and "login" not in url.lower(),
                timeout=600_000,
            )
        except Exception:
            pass

    def _work():
        try:
            _run_with_browser(_open)
        except Exception as e:
            app.logger.exception("Login browser launch failed: %s", e)
            db.set_setting("last_error", f"login: {type(e).__name__}: {e}")

    threading.Thread(target=_work, daemon=True).start()
    flash("Browser opening — log in to RSI, then close the window.", "info")
    return redirect(url_for("dashboard"))


@app.route("/diagnose")
def diagnose():
    """Synchronously probe Playwright / Chromium and return a plain-text report.
    Useful for debugging frozen-build issues where the background thread fails silently.
    """
    import platform
    lines = []
    lines.append(f"Platform: {platform.platform()}")
    lines.append(f"Data dir: {paths.data_dir()}")
    lines.append(f"Browser profile: {paths.browser_profile_dir()}")
    lines.append(f"Last error (from settings): {db.get_setting('last_error', '(none)')}")
    lines.append("")
    lines.append("--- Playwright test ---")
    try:
        from playwright.sync_api import sync_playwright
        lines.append("playwright module: imported OK")
        with sync_playwright() as p:
            lines.append(f"sync_playwright ready; chromium path: {p.chromium.executable_path}")
            bc = p.chromium.launch_persistent_context(
                user_data_dir=str(paths.browser_profile_dir()),
                headless=True,
                timeout=20000,
            )
            lines.append("launched persistent context OK (headless)")
            bc.close()
            lines.append("closed context OK")
        lines.append("RESULT: OK")
    except Exception as e:
        app.logger.exception("diagnose failed")
        lines.append(f"RESULT: FAILED — {type(e).__name__}: {e}")
    return "<pre>" + "\n".join(lines) + "</pre>"


@app.route("/lobbies", methods=["POST"])
def add_lobby():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    if not name or not url:
        flash("Name and URL are required.", "error")
    else:
        db.add_lobby(name, url)
        flash(f"Added lobby {name}.", "info")
    return redirect(url_for("dashboard"))


@app.route("/lobbies/<int:lobby_id>/delete", methods=["POST"])
def delete_lobby(lobby_id):
    db.delete_lobby(lobby_id)
    return redirect(url_for("dashboard"))


@app.route("/lobbies/discover", methods=["POST"])
def discover_lobbies_route():
    try:
        lobbies = _run_with_browser(lambda ctx: discover.discover_lobbies(ctx))
    except discover.NotLoggedInError as e:
        flash(str(e) + " Click 'Open browser & log in' below first.", "error")
        return redirect(url_for("dashboard"))
    except Exception as e:
        app.logger.exception("discovery failed")
        db.set_setting("last_error", f"discover: {type(e).__name__}: {e}")
        flash(f"Discovery failed: {e}", "error")
        return redirect(url_for("dashboard"))
    if not lobbies:
        flash("No lobbies returned — Spectrum layout may have changed.", "error")
        return redirect(url_for("dashboard"))
    before = {l["url"] for l in db.list_lobbies()}
    for l in lobbies:
        db.add_lobby(l["name"], l["url"])
    after = {l["url"] for l in db.list_lobbies()}
    new = len(after - before)
    flash(f"Found {len(lobbies)} lobbies — added {new} new.", "info")
    return redirect(url_for("dashboard"))


@app.route("/scrape/<int:lobby_id>", methods=["POST"])
def scrape(lobby_id):
    lobby = db.get_lobby(lobby_id)
    if not lobby:
        flash("Lobby not found.", "error")
        return redirect(url_for("dashboard"))

    def _work():
        try:
            result = _run_with_browser(
                lambda ctx: scraper.scrape_lobby(ctx, lobby["url"], lobby["id"])
            )
            app.logger.info(f"Scrape complete: {result}")
        except scraper.NotLoggedInError as e:
            app.logger.warning("Scrape blocked: %s", e)
        except Exception as e:
            app.logger.exception(f"Scrape failed: {e}")

    threading.Thread(target=_work, daemon=True).start()
    flash(f"Scraping {lobby['name']}… check the browser window.", "info")
    return redirect(url_for("queue"))


@app.route("/queue")
def queue():
    submitted = request.args.get("submitted") == "1"
    if submitted:
        # Form was submitted — trust exactly what came back. Missing checkbox = unchecked.
        groups_param = request.args.getlist("group")
        only_online = request.args.get("online") == "1"
        exclude_menus = request.args.get("exclude_menus") == "1"
        only_unsent = request.args.get("unsent") == "1"
    else:
        # Fresh page load — apply sensible defaults.
        groups_param = ["BACKER", "CIVILIAN"]
        only_online = True
        exclude_menus = True
        only_unsent = True
    search = request.args.get("q", "").strip() or None

    recruits = db.list_recruits(
        groups=groups_param,
        only_online=only_online,
        exclude_substatus=["In Menus"] if exclude_menus else None,
        only_unsent=only_unsent,
        search=search,
    )
    templates = db.list_templates()
    active = next((t for t in templates if t["is_active"]), None)
    return render_template(
        "queue.html",
        recruits=recruits,
        groups=groups_param,
        only_online=only_online,
        exclude_menus=exclude_menus,
        only_unsent=only_unsent,
        search=search or "",
        templates=templates,
        active_template_id=active["id"] if active else None,
    )


@app.route("/recruits/<int:recruit_id>/delete", methods=["POST"])
def remove_recruit(recruit_id):
    db.delete_recruit(recruit_id)
    return ("", 204)


@app.route("/compose", methods=["GET", "POST"])
def compose():
    if request.method == "POST":
        name = request.form.get("name", "Default").strip() or "Default"
        body = request.form.get("body", "").strip()
        if not body:
            flash("Message body is required.", "error")
        else:
            db.save_template(name, body, make_active=True)
            flash("Template saved and set as default.", "info")
        return redirect(url_for("compose"))
    active = db.get_active_template()
    all_templates = db.list_templates()
    return render_template("compose.html", active=active, templates=all_templates)


@app.route("/templates/<int:template_id>/delete", methods=["POST"])
def delete_template_route(template_id):
    db.delete_template(template_id)
    return redirect(url_for("compose"))


@app.route("/templates/<int:template_id>/activate", methods=["POST"])
def activate_template_route(template_id):
    db.set_active_template(template_id)
    return redirect(url_for("compose"))


@app.route("/send/<int:recruit_id>", methods=["POST"])
def send(recruit_id):
    recruit = db.get_recruit(recruit_id)
    if not recruit:
        return jsonify({"ok": False, "error": "recruit not found"}), 404

    template_id = request.form.get("template_id", type=int)
    template = db.get_template(template_id) if template_id else db.get_active_template()
    if not template:
        return jsonify({"ok": False, "error": "no message template selected"}), 400

    # Re-fetch with lobby join for template rendering
    rows = db.list_recruits(only_unsent=False)
    row = next((r for r in rows if r["id"] == recruit_id), None)
    if not row:
        return jsonify({"ok": False, "error": "recruit not found in join"}), 404

    message = sender.render_message(template["body"], row)

    try:
        result, err = _run_with_browser(lambda ctx: sender.send_dm(ctx, row, message))
    except Exception as e:
        db.mark_sent(recruit_id, sender.SendResult.ERROR, str(e))
        return jsonify({"ok": False, "result": sender.SendResult.ERROR, "error": str(e)}), 500

    db.mark_sent(recruit_id, result, err)
    return jsonify({"ok": result == sender.SendResult.SENT, "result": result, "error": err})


if __name__ == "__main__":
    db.init()
    port = int(os.environ.get("SC_RECRUITER_PORT", "5050"))
    app.run(host="127.0.0.1", port=port, debug=False)
