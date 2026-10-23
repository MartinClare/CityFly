"""Post approved magazine stories to the Facebook Page (link + short hook).

Runs on the cloud robot after web publish / on a daily cron. Skips when
FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN is missing. Never double-posts:
stores facebook.post_id on the draft meta.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from common.config import load_env

logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"
HKT = ZoneInfo("Asia/Hong_Kong")

# Per run (approve export or cron). Override with FACEBOOK_MAX_PER_RUN; 0 = no cap.
DEFAULT_FACEBOOK_MAX_PER_RUN = 2
MAX_MESSAGE_LEN = 500
_HOOK_MAX = 180

_LEGACY_CAPTION_MARKERS = (
    "邊度有窗口",
    "未證實的傳聞",
)


def _public_base() -> str:
    load_env()
    return (
        os.getenv("PUBLIC_SITE_URL")
        or os.getenv("MAGAZINE_SITE_URL")
        or "https://web-eight-ebon-98.vercel.app"
    ).rstrip("/")


def _creds() -> tuple[str, str] | None:
    load_env()
    page = (os.getenv("FACEBOOK_PAGE_ID") or "").strip()
    token = (os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
    if not page or not token or token.startswith("replace"):
        return None
    return page, token


def story_url(slug: str) -> str:
    return f"{_public_base()}/stories/{slug}"


def _wait_public(url: str, *, tries: int = 6, delay: float = 8.0) -> bool:
    for i in range(tries):
        try:
            resp = requests.head(url, timeout=15, allow_redirects=True)
            if resp.status_code == 405:
                resp = requests.get(url, timeout=15, allow_redirects=True)
            if resp.status_code == 200:
                return True
            logger.info("Public story not ready %s -> %s (try %d)", url, resp.status_code, i + 1)
        except Exception as exc:
            logger.info("Public story check failed %s: %s", url, exc)
        time.sleep(delay)
    return False


def _first_sentence(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    for sep in ("。", "！", "？", "\n"):
        if sep in text:
            return text.split(sep, 1)[0].strip() + (sep if sep != "\n" else "")
    return text


def _is_legacy_boilerplate_caption(caption: str) -> bool:
    return any(m in caption for m in _LEGACY_CAPTION_MARKERS)


def _hook_line(meta: dict[str, Any]) -> str:
    headline = (meta.get("headline") or "").strip()
    fb = meta.get("facebook") or {}
    thesis = (fb.get("visual_thesis") or "").strip()
    dek = ((meta.get("web") or {}).get("excerpt") or meta.get("dek") or "").strip()
    for raw in (thesis, _first_sentence(dek), headline):
        line = (raw or "").strip()
        if not line:
            continue
        if line == headline and len(line) > _HOOK_MAX:
            return line[:_HOOK_MAX].rstrip() + "…"
        if len(line) > _HOOK_MAX:
            return line[:_HOOK_MAX].rstrip() + "…"
        return line
    return headline[:_HOOK_MAX]


def _comment_invite(meta: dict[str, Any]) -> str:
    fb = meta.get("facebook") or {}
    for key in ("comment_invite", "question", "invite"):
        invite = (fb.get(key) or "").strip()
        if invite:
            return invite

    pillar = (meta.get("pillar") or "").lower()
    district = (meta.get("district") or "").strip()

    by_pillar = {
        "property": "規劃圖之外，你覺得落地時最大阻力會係邊一環？",
        "economy": "條數亮眼，邊個群體先感受到代价或紅利？",
        "transport": "如果只改一個環節，邊樣改動才真正郁到街坊日常？",
        "environment": "環評過咗之後，社區仲要守住咩？",
        "culture": "保留同發展之間，你會點劃條界？",
    }
    if pillar in by_pillar:
        return by_pillar[pillar]
    if district and district not in ("香港", "全港"):
        return f"喺{district}呢單發展，你覺得仲欠嘅係配套定時間表？"
    return "讀完你會問政府或市場邊一個決定？"


def build_teaser_message(meta: dict[str, Any]) -> str:
    """Short playbook-style hook + one precise comment invite (Traditional Chinese)."""
    hook = _hook_line(meta)
    invite = _comment_invite(meta)
    return f"{hook}\n\n{invite}"


def _message(meta: dict[str, Any]) -> str:
    fb = meta.get("facebook") or {}
    caption = (fb.get("caption") or "").strip()
    if caption and not _is_legacy_boilerplate_caption(caption):
        return caption[:MAX_MESSAGE_LEN]
    return build_teaser_message(meta)[:MAX_MESSAGE_LEN]


def _already_posted(meta: dict[str, Any]) -> bool:
    if meta.get("facebook_post_id"):
        return True
    fb = meta.get("facebook") or {}
    return bool(fb.get("post_id"))


def _placement_rank(meta: dict[str, Any]) -> int:
    p = (meta.get("placement") or "").lower()
    if p == "a1":
        return 0
    if p == "a2":
        return 1
    return 2


def pending_approved(*, lookback_days: int = 14) -> list[tuple[str, str, dict[str, Any], Path]]:
    """(day, slug, meta, json_path) for approved stories not yet on Facebook."""
    from hk_city.desk.drafts_store import DRAFTS

    cutoff = (datetime.now(HKT).date() - timedelta(days=lookback_days)).isoformat()
    out: list[tuple[str, str, dict[str, Any], Path]] = []
    if not DRAFTS.is_dir():
        return out
    for day_dir in DRAFTS.iterdir():
        if not day_dir.is_dir():
            continue
        day = day_dir.name
        if day < cutoff or not day[:1].isdigit():
            continue
        for js in day_dir.glob("*.json"):
            try:
                meta = json.loads(js.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(meta, dict):
                continue
            if (meta.get("status") or "") != "approved":
                continue
            if _already_posted(meta):
                continue
            slug = meta.get("slug") or js.stem
            out.append((day, slug, meta, js))
    # Newest edition first; within a day prefer A1 then A2
    out.sort(
        key=lambda row: (
            -int((row[0] or "0").replace("-", "") or 0),
            _placement_rank(row[2]),
            row[1],
        )
    )
    return out


def _graph_post(page_id: str, token: str, *, message: str, link: str) -> str:
    resp = requests.post(
        f"{GRAPH}/{page_id}/feed",
        data={
            "message": message,
            "link": link,
            "access_token": token,
        },
        timeout=45,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not data.get("id"):
        raise RuntimeError(f"Facebook Graph error {resp.status_code}: {data}")
    return str(data["id"])


def post_one(day: str, slug: str, meta: dict[str, Any], js: Path, *, creds: tuple[str, str]) -> dict[str, Any]:
    page_id, token = creds
    url = story_url(slug)
    if not _wait_public(url):
        return {"ok": False, "slug": slug, "reason": "public_url_not_ready", "url": url}
    message = _message(meta)
    post_id = _graph_post(page_id, token, message=message, link=url)
    fb = dict(meta.get("facebook") or {})
    fb["post_id"] = post_id
    fb["posted_at"] = datetime.now(timezone.utc).isoformat()
    fb["link"] = url
    meta["facebook"] = fb
    meta["facebook_post_id"] = post_id
    js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Facebook posted %s -> %s", slug, post_id)
    return {"ok": True, "slug": slug, "post_id": post_id, "url": url}


def _max_per_run_from_env() -> int:
    raw = (os.getenv("FACEBOOK_MAX_PER_RUN") or "").strip()
    if not raw:
        return DEFAULT_FACEBOOK_MAX_PER_RUN
    return int(raw)


def post_pending(*, limit: int | None = None, lookback_days: int | None = None) -> dict[str, Any]:
    """Post approved stories not yet on Facebook.

    Default cap is ``DEFAULT_FACEBOOK_MAX_PER_RUN`` per run (A1 before A2 within each
    edition). Set ``FACEBOOK_MAX_PER_RUN=0`` for no cap, or a higher positive int.
    """
    load_env()
    creds = _creds()
    if not creds:
        logger.info("Facebook skipped; FACEBOOK_PAGE_ID / FACEBOOK_PAGE_ACCESS_TOKEN not set")
        return {"ok": False, "skipped": "no_credentials", "posted": 0}

    if limit is None:
        limit = _max_per_run_from_env()
    if lookback_days is None:
        lookback_days = int(os.getenv("FACEBOOK_LOOKBACK_DAYS", "14"))

    pending_all = pending_approved(lookback_days=lookback_days)
    pending = pending_all if limit <= 0 else pending_all[:limit]
    results: list[dict[str, Any]] = []
    auth_dead = False
    for day, slug, meta, js in pending:
        if auth_dead:
            results.append({"ok": False, "slug": slug, "reason": "skipped_after_auth_error"})
            continue
        try:
            results.append(post_one(day, slug, meta, js, creds=creds))
            time.sleep(2)
        except Exception as exc:
            reason = str(exc)
            logger.error("Facebook post failed for %s: %s", slug, reason)
            results.append({"ok": False, "slug": slug, "reason": reason})
            # Only abort the batch on expired/invalid token — not on link scrape
            # or other per-story Graph errors (those should not block the rest).
            if "code': 190" in reason or "Session has expired" in reason or "Error validating access token" in reason:
                auth_dead = True

    posted = sum(1 for r in results if r.get("ok"))
    summary = {
        "ok": True,
        "posted": posted,
        "attempted": len(results),
        "pending_left": max(0, len(pending_approved(lookback_days=lookback_days)) - posted),
        "public_base": _public_base(),
        "auth_error": auth_dead,
        "results": results,
    }
    logger.info(
        "Facebook batch %s",
        {k: summary[k] for k in ("posted", "attempted", "pending_left", "public_base", "auth_error")},
    )
    return summary
