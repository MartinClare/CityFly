"""City Fly robot desk — FastAPI multi-page editor portal."""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer
from starlette.middleware.base import BaseHTTPMiddleware

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

load_dotenv(ROOT / ".env")

from hk_city.desk import drafts_store as drafts
from hk_city.desk.settings_store import (
    FEED_GROUPS,
    GROUP_LABELS,
    ensure_settings,
    load_yaml_raw,
    save_settings,
)

DESK_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(DESK_DIR / "templates"))
SESSION_COOKIE = "cityfly_desk"
USER_NAME = "editor"

JOBS: dict[str, dict[str, Any]] = {}
JOB_LOCK = threading.Lock()


def _password() -> str:
    return os.environ.get("DESK_PASSWORD", "")


def _secret() -> str:
    key = os.environ.get("DESK_SECRET", "").strip()
    if key:
        return key
    env_path = ROOT / ".env"
    key = secrets.token_urlsafe(32)
    # append if missing
    if env_path.exists():
        text = env_path.read_text(encoding="utf-8")
        if "DESK_SECRET=" not in text:
            with env_path.open("a", encoding="utf-8") as f:
                f.write(f"\nDESK_SECRET={key}\n")
    os.environ["DESK_SECRET"] = key
    return key


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(_secret(), salt="cityfly-desk-session")


def _bind() -> str:
    return os.environ.get("DESK_BIND", "127.0.0.1")


def _port() -> int:
    return int(os.environ.get("DESK_PORT", "8787"))


def create_session_token() -> str:
    return _serializer().dumps({"user": USER_NAME})


def read_session(request: Request) -> str | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        data = _serializer().loads(raw)
    except BadSignature:
        return None
    if data.get("user") != USER_NAME:
        return None
    return USER_NAME


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        public = path in {"/login", "/favicon.ico"} or path.startswith("/static/")
        if public:
            return await call_next(request)
        if read_session(request):
            return await call_next(request)
        if path.startswith("/api/"):
            return Response("unauthorized", status_code=401)
        nxt = quote(str(request.url.path) + (("?" + request.url.query) if request.url.query else ""))
        return RedirectResponse(f"/login?next={nxt}", status_code=303)


app = FastAPI(title="City Fly Desk", docs_url=None, redoc_url=None)
app.add_middleware(AuthMiddleware)
app.mount("/static", StaticFiles(directory=str(DESK_DIR / "static")), name="static")


def _ctx(request: Request, **extra: Any) -> dict[str, Any]:
    base = {
        "request": request,
        "user": read_session(request),
        "statuses": drafts.STATUSES,
        "nav": True,
    }
    base.update(extra)
    return base


def render(request: Request, name: str, context: dict[str, Any] | None = None, status_code: int = 200):
    ctx = dict(context or {})
    ctx.setdefault("request", request)
    return TEMPLATES.TemplateResponse(request, name, ctx, status_code=status_code)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/", error: str = ""):
    if read_session(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html", {"next": next or "/", "error": error, "nav": False},)


@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    expected = _password()
    if not expected:
        return render(request, "login.html", {"next": next or "/",
                "error": "未設定 DESK_PASSWORD。",
                "nav": False,
            },
            status_code=400,)
    if username != USER_NAME or password != expected:
        return render(request, "login.html", {"next": next or "/",
                "error": "帳戶或密碼唔啱。",
                "nav": False,
            },
            status_code=401,)
    dest = next if next.startswith("/") else "/"
    resp = RedirectResponse(dest, status_code=303)
    resp.set_cookie(
        SESSION_COOKIE,
        create_session_token(),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 14,
    )
    return resp


@app.post("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/", response_class=HTMLResponse)
async def inbox(request: Request, day: str = "", status: str = "draft_pending_review"):
    day_list = drafts.days()
    day = day or (day_list[0] if day_list else "")
    rows = drafts.packs(day, status=status) if day else []
    return render(request, "inbox.html", _ctx(
            request,
            title="稿件",
            day=day,
            days=day_list,
            status=status,
            rows=rows,
            active="articles",
        ),)


@app.get("/a/{day}/{slug}", response_class=HTMLResponse)
async def article(request: Request, day: str, slug: str, queue: str = "draft_pending_review"):
    try:
        raw, meta, _, _ = drafts.load_pack(day, slug)
    except FileNotFoundError:
        return RedirectResponse("/", status_code=303)
    parts = drafts.parse_article_parts(raw)
    status = meta.get("status") or "draft_pending_review"
    job_key = f"{day}/{slug}"
    with JOB_LOCK:
        job = dict(JOBS.get(job_key) or {})
    remain = 0
    seen = False
    for row in drafts.packs(day):
        if row["slug"] == slug:
            seen = True
            continue
        if seen and (queue == "all" or row["status"] == queue):
            remain += 1
    nav = drafts.neighbors(day, slug, queue)
    return render(request, "article.html", _ctx(
            request,
            title=parts["title"] or slug,
            day=day,
            slug=slug,
            queue=queue,
            status=status,
            status_label=drafts.STATUSES.get(status, status),
            cjk=drafts.cjk_len(raw),
            parts=parts,
            html_body=drafts.md_to_html(raw),
            remain=remain,
            job=job,
            busy=job.get("state") == "running",
            active="articles",
            refresh=job.get("state") == "running",
            nav_prev=nav.get("prev"),
            nav_next=nav.get("next"),
            nav_index=nav.get("index") or 0,
            nav_total=nav.get("total") or 0,
        ),)


@app.post("/a/{day}/{slug}/status")
async def article_status(
    day: str,
    slug: str,
    status: str = Form(...),
    queue: str = Form("draft_pending_review"),
):
    try:
        drafts.set_status(day, slug, status)
    except (ValueError, FileNotFoundError):
        return RedirectResponse(f"/a/{day}/{slug}?queue={queue}", status_code=303)
    if status == "needs_edit":
        return RedirectResponse(f"/a/{day}/{slug}?queue={queue}", status_code=303)
    return RedirectResponse(drafts.next_location(day, slug, queue), status_code=303)


@app.post("/a/{day}/{slug}/save")
async def article_save(
    day: str,
    slug: str,
    title: str = Form(...),
    dek: str = Form(""),
    body: str = Form(""),
    queue: str = Form("draft_pending_review"),
):
    try:
        drafts.save_edits(day, slug, title=title, dek=dek, body=body)
    except FileNotFoundError:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/a/{day}/{slug}?queue={queue}&saved=1", status_code=303)


@app.post("/a/{day}/{slug}/delete")
async def article_delete(day: str, slug: str, queue: str = Form("draft_pending_review")):
    try:
        loc = drafts.next_location(day, slug, queue)
        drafts.delete_pack(day, slug)
    except FileNotFoundError:
        return RedirectResponse("/", status_code=303)
    if f"/{slug}" in loc:
        return RedirectResponse(f"/?day={day}&status={queue}", status_code=303)
    return RedirectResponse(loc, status_code=303)


def _start_regen(day: str, slug: str, kind: str) -> None:
    key = f"{day}/{slug}"
    with JOB_LOCK:
        current = JOBS.get(key) or {}
        if current.get("state") == "running":
            return
        JOBS[key] = {"kind": kind, "state": "running", "error": ""}

    def work() -> None:
        try:
            from desk_regen import regen_image, regen_text

            if kind == "image":
                regen_image(day, slug)
            else:
                regen_text(day, slug)
            with JOB_LOCK:
                JOBS[key] = {"kind": kind, "state": "done", "error": ""}
        except Exception as exc:
            with JOB_LOCK:
                JOBS[key] = {"kind": kind, "state": "error", "error": str(exc)}

    threading.Thread(target=work, daemon=True).start()


@app.post("/a/{day}/{slug}/regen")
async def article_regen(
    day: str,
    slug: str,
    kind: str = Form(...),
    queue: str = Form("draft_pending_review"),
):
    try:
        drafts.set_status(day, slug, "needs_edit")
    except Exception:
        pass
    if kind in {"image", "text"}:
        _start_regen(day, slug, kind)
    return RedirectResponse(f"/a/{day}/{slug}?queue={queue}", status_code=303)


@app.get("/images/{name}")
async def serve_image(name: str):
    if "/" in name or ".." in name:
        return Response(status_code=400)
    for day in drafts.days():
        p = drafts.DRAFTS / day / "images" / name
        if p.exists():
            data = p.read_bytes()
            ctype = "image/jpeg" if p.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
            return Response(data, media_type=ctype, headers={"Cache-Control": "no-store"})
    return Response(status_code=404)


@app.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request, saved: str = ""):
    settings = ensure_settings()
    base = load_yaml_raw()
    groups = []
    for name in FEED_GROUPS:
        yaml_group = (base.get("collectors") or {}).get(name) or {}
        state = (settings.get("collectors") or {}).get(name) or {}
        feeds = []
        by_url = {(f.get("url") or ""): f for f in (state.get("feeds") or [])}
        for feed in yaml_group.get("feeds") or []:
            url = feed.get("url") or ""
            flag = by_url.get(url) or {}
            feeds.append(
                {
                    **feed,
                    "enabled": bool(flag.get("enabled", True)),
                }
            )
        groups.append(
            {
                "name": name,
                "label": GROUP_LABELS.get(name, name),
                "enabled": bool(state.get("enabled", True)),
                "limit": int(state.get("limit") or yaml_group.get("limit") or 40),
                "feeds": feeds,
                "extra_feeds": state.get("extra_feeds") or [],
            }
        )
    return render(request, "sources.html", _ctx(request, title="來源", groups=groups, saved=bool(saved), active="sources"),)


@app.post("/sources")
async def sources_save(request: Request):
    form = await request.form()
    settings = ensure_settings()
    base = load_yaml_raw()
    collectors = settings.setdefault("collectors", {})
    for name in FEED_GROUPS:
        yaml_group = (base.get("collectors") or {}).get(name) or {}
        slot = collectors.setdefault(name, {"enabled": True, "limit": 40, "feeds": [], "extra_feeds": []})
        slot["enabled"] = form.get(f"group_enabled_{name}") == "on"
        try:
            slot["limit"] = int(form.get(f"group_limit_{name}") or slot.get("limit") or 40)
        except ValueError:
            pass
        feed_rows = []
        for feed in yaml_group.get("feeds") or []:
            url = feed.get("url") or ""
            key = f"feed_{name}_{url}"
            # checkbox names can't have arbitrary URLs easily — use index
            feed_rows.append({"url": url, "enabled": True})
        # rebuild from indexed checkboxes
        feed_rows = []
        for i, feed in enumerate(yaml_group.get("feeds") or []):
            url = feed.get("url") or ""
            feed_rows.append(
                {
                    "url": url,
                    "enabled": form.get(f"feed_{name}_{i}") == "on",
                }
            )
        slot["feeds"] = feed_rows
        # keep existing extras unless deleted
        extras = list(slot.get("extra_feeds") or [])
        kept_extras = []
        for i, extra in enumerate(extras):
            if form.get(f"extra_del_{name}_{i}") == "on":
                continue
            extra = dict(extra)
            extra["enabled"] = form.get(f"extra_on_{name}_{i}") == "on"
            kept_extras.append(extra)
        new_name = (form.get(f"new_name_{name}") or "").strip()
        new_url = (form.get(f"new_url_{name}") or "").strip()
        new_kind = (form.get(f"new_kind_{name}") or "rss").strip()
        new_policy = (form.get(f"new_policy_{name}") or "rss_only").strip()
        if new_url:
            kept_extras.append(
                {
                    "name": new_name or "自訂來源",
                    "url": new_url,
                    "kind": new_kind if new_kind in {"rss", "html"} else "rss",
                    "policy": new_policy
                    if new_policy in {"rss_only", "public_page_extract_allowed", "metadata_only"}
                    else "rss_only",
                    "tier": 3,
                    "enabled": True,
                }
            )
        slot["extra_feeds"] = kept_extras
    save_settings(settings)
    return RedirectResponse("/sources?saved=1", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, saved: str = ""):
    settings = ensure_settings()
    base = load_yaml_raw()
    pillars = []
    flags = settings.get("pillars") or {}
    for p in base.get("pillars") or []:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        pillars.append(
            {
                "id": pid,
                "label": p.get("label") or pid,
                "enabled": bool(flags.get(pid, True)),
            }
        )
    return render(request, "settings.html", _ctx(
            request,
            title="設定",
            settings=settings,
            pillars=pillars,
            health=drafts.health_text(),
            saved=bool(saved),
            active="settings",
        ),)


@app.post("/settings")
async def settings_save(request: Request):
    form = await request.form()
    settings = ensure_settings()
    for key in ("news_limit", "max_article_drafts", "ledger_lookback_days"):
        try:
            settings[key] = int(form.get(key) or settings.get(key) or 0)
        except ValueError:
            pass
    base = load_yaml_raw()
    flags = {}
    for p in base.get("pillars") or []:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if not pid:
            continue
        flags[pid] = form.get(f"pillar_{pid}") == "on"
    settings["pillars"] = flags
    save_settings(settings)
    return RedirectResponse("/settings?saved=1", status_code=303)


@app.get("/health", response_class=HTMLResponse)
async def health_page(request: Request):
    return render(request, "health.html", _ctx(request, title="機器人", health=drafts.health_text(), active="health"),)


def main() -> None:
    import uvicorn

    bind = _bind()
    port = _port()
    if bind not in {"127.0.0.1", "localhost"} and not _password():
        raise SystemExit("DESK_PASSWORD required when DESK_BIND is public")
    print(f"Review portal http://{bind}:{port}", flush=True)
    uvicorn.run(app, host=bind, port=port, log_level="warning")


if __name__ == "__main__":
    main()
