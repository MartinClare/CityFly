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


def _message(meta: dict[str, Any]) -> str:
    fb = meta.get("facebook") or {}
    caption = (fb.get("caption") or "").strip()
    if caption:
        return caption[:500]
    headline = (meta.get("headline") or "").strip()
    dek = ((meta.get("web") or {}).get("excerpt") or meta.get("dek") or "").strip()
    bits = [b for b in (headline, dek) if b]
    return "\n\n".join(bits)[:500]


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


def post_pending(*, limit: int | None = None, lookback_days: int | None = None) -> dict[str, Any]:
    """Post approved stories not yet on Facebook.

    `limit` None/0 (default) = no cap — post every pending story in the lookback
    window. Set FACEBOOK_MAX_PER_RUN to a positive int only if you want a hard cap.
    """
    load_env()
    creds = _creds()
    if not creds:
        logger.info("Facebook skipped; FACEBOOK_PAGE_ID / FACEBOOK_PAGE_ACCESS_TOKEN not set")
        return {"ok": False, "skipped": "no_credentials", "posted": 0}

    if limit is None:
        raw = (os.getenv("FACEBOOK_MAX_PER_RUN") or "0").strip()
        limit = int(raw) if raw else 0
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
