"""Post approved magazine stories to the Facebook Page.

Hybrid posts: FB-only callout image (unpublished photo) + feed item with
public story `link`. Caps daily volume by attractiveness score. Web heroes
are never overwritten.

Runs on the cloud robot after web publish / on a daily cron. Skips when
FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN is missing. Never double-posts:
stores facebook.post_id on the draft meta.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from common.config import load_env
from hk_city.facebook_image import compose_for_draft

logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v21.0"
HKT = ZoneInfo("Asia/Hong_Kong")
# Daily cadence: 3 morning + 3 noon + 4 evening = 10
FB_SLOT_QUOTAS: dict[str, int] = {
    "morning": 3,
    "noon": 3,
    "evening": 4,
}
DEFAULT_FB_CAP = FB_SLOT_QUOTAS["morning"]


def fb_slot_for_now(now: datetime | None = None) -> str:
    """HKT daypart for Facebook cron windows (07:30 / 12:00 / 18:00)."""
    local = now.astimezone(HKT) if now else datetime.now(HKT)
    hour = local.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 17:
        return "noon"
    return "evening"


def fb_slot_quota(slot: str | None = None) -> tuple[str, int]:
    name = (slot or fb_slot_for_now()).strip().lower()
    if name not in FB_SLOT_QUOTAS:
        name = fb_slot_for_now()
    return name, FB_SLOT_QUOTAS[name]


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


def share_url(slug: str) -> str:
    """OG share landing that can prefer FB callout art (fallback path)."""
    return f"{_public_base()}/stories/{slug}/share"


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


# Legacy desk slogan — strip from old captions; never append again.
_LEGACY_SLOGAN = (
    "生意、投資觀察、建造，邊度有窗口？"
    "生活會點變，有咩威脅，定係仲有未證實的傳聞？"
)
_LEGACY_SLOGAN_RE = re.compile(
    r"(?:\n\n)?生意、投資觀察、建造，邊度有窗口？\s*"
    r"生活會點變，有咩威脅，定係仲有未證實的傳聞？\s*$"
)


def _heuristic_question(meta: dict[str, Any]) -> str:
    """Written-Chinese hook question from pillar / headline cues."""
    pillar = (meta.get("pillar") or "").lower()
    headline = (meta.get("headline") or meta.get("title") or "").strip()
    if pillar in {"property", "housing"} or any(k in headline for k in ("樓", "呎", "盤", "居屋", "交吉")):
        return "這個價位與時機，你會進場還是觀望？"
    if pillar in {"tech", "technology"} or any(k in headline for k in ("AI", "手機", "App", "雲端", "私隱")):
        return "你會先用起來，還是再觀望一輪？"
    if pillar in {"economy", "markets"} or any(k in headline for k in ("恒指", "息", "出口", "失業")):
        return "對你的收入或工作，最直接的影響是哪一項？"
    if pillar in {"mobility", "transport"} or any(k in headline for k in ("車", "鐵", "船", "口岸", "加價")):
        return "你的日常路線會不會因此改寫？"
    return "你怎麼看？歡迎留言你的判斷。"


def closing_question_for_draft(meta: dict[str, Any]) -> str:
    """One attention-drawing question for the end of a FB post."""
    fb = meta.get("facebook") or {}
    cached = (fb.get("closing_question") or "").strip()
    if cached.endswith("？") or cached.endswith("?"):
        return cached[:60]

    from common import llm

    headline = (meta.get("headline") or meta.get("title") or "").strip()
    excerpt = (
        ((meta.get("web") or {}).get("excerpt") or "")
        or (meta.get("dek") or "")
        or ""
    ).strip()[:200]
    if llm.available() and headline:
        try:
            raw = llm.chat(
                "Write ONE Traditional Chinese question in written magazine Chinese "
                "(書面中文, not spoken Cantonese) that ends a Facebook news post and "
                "invites comments. Max 28 characters. Must end with ？ Only output the question.",
                f"headline: {headline}\nexcerpt: {excerpt}",
                temperature=0.4,
                max_tokens=1024,
                reasoning_effort="low",
            )
            q = (raw or "").strip().splitlines()[0].strip().strip("「」\"'")
            if "？" not in q and "?" not in q:
                q = q.rstrip("。.!！") + "？"
            if q and "生意、投資觀察" not in q and len(q) <= 40:
                return q
        except Exception as exc:
            logger.warning("FB closing question LLM failed: %s", exc)
    return _heuristic_question(meta)


# Fixed brand stamp under every FB caption (humans, not algorithm).
FB_BRAND_CLOSER = "CS Magazine · 城市觀察"
_BRAND_CLOSER_RE = re.compile(
    r"(?:\n\n)?(?:City Sight[^\n]*|CS Magazine[^\n]*城市觀察)\s*$"
)


def _message(meta: dict[str, Any]) -> str:
    """Caption body + hook question + brand closer (never the legacy desk slogan)."""
    fb = dict(meta.get("facebook") or {})
    caption = (fb.get("caption") or "").strip()
    if caption:
        caption = _LEGACY_SLOGAN_RE.sub("", caption).rstrip()
        if _LEGACY_SLOGAN in caption:
            caption = caption.replace(_LEGACY_SLOGAN, "").rstrip()
        caption = _BRAND_CLOSER_RE.sub("", caption).rstrip()
    if not caption:
        headline = (meta.get("headline") or "").strip()
        dek = ((meta.get("web") or {}).get("excerpt") or meta.get("dek") or "").strip()
        caption = "\n\n".join(b for b in (headline, dek) if b)

    parts = [p for p in caption.split("\n\n") if p.strip()]
    # Drop a trailing brand line if the stored caption already had one
    if parts and "城市觀察" in parts[-1] and "CS Magazine" in parts[-1]:
        parts = parts[:-1]
    tail = parts[-1].strip() if parts else ""
    has_hook_q = (
        bool(tail)
        and (tail.endswith("？") or tail.endswith("?"))
        and "生意、投資觀察" not in tail
        and len(tail) <= 40
        and "\n" not in tail
    )
    if has_hook_q:
        body = "\n\n".join(parts[:-1]).strip()
        question = tail
    else:
        body = "\n\n".join(parts).strip() if parts else caption.strip()
        question = closing_question_for_draft(meta)
        fb["closing_question"] = question
        meta["facebook"] = fb

    chunks = [c for c in (body, question, FB_BRAND_CLOSER) if c]
    return "\n\n".join(chunks)[:500]


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


def _hook_quality(headline: str) -> float:
    h = headline or ""
    score = 0.0
    if re.search(r"\d", h):
        score += 8
    if any(k in h for k in ("：", ":", "不", "卻", "反而", "終於", "不再", "首次")):
        score += 4
    if 6 <= len(re.findall(r"[\u4e00-\u9fff]", h)) <= 18:
        score += 2
    return score


def fb_attractiveness(meta: dict[str, Any]) -> float:
    """Deterministic share-worthiness for Facebook ranking."""
    score = 0.0
    placement = (meta.get("placement") or "").lower()
    if placement == "a1":
        score += 100
    elif placement == "a2":
        score += 50
    interest = int(meta.get("interest") or 0)
    score += interest * 8
    ent = (meta.get("entertainment") or "").lower()
    if ent == "high":
        score += 12
    elif ent == "medium":
        score += 5
    if meta.get("future_life"):
        score += 15
    if meta.get("advanced_tech") and not meta.get("gov_tech_pr"):
        score += 8
    from hk_city.growth_formats import FB_GROWTH_BOOST, is_growth_format

    fmt = (meta.get("format") or "").lower()
    if is_growth_format(fmt):
        score += float(FB_GROWTH_BOOST.get(fmt, 12))
    synthesis = (meta.get("synthesis") or "").lower()
    cluster = int(meta.get("cluster_size") or len(meta.get("sources") or []) or 1)
    if synthesis in {"multi_source", "cousin_feature"} or cluster >= 2:
        score += 10
    score += _hook_quality(meta.get("headline") or "")
    if meta.get("gov_tech_pr"):
        score -= 15
    # Thin single-source dull on local feeds — but overseas tech is often one outlet only.
    single_ok = bool(
        meta.get("future_life")
        or meta.get("advanced_tech")
        or synthesis == "single_authority"
        or is_growth_format(fmt)
    )
    if cluster <= 1 and not single_ok:
        score -= 10
    if meta.get("already_covered"):
        score -= 10
    score += float(meta.get("score") or meta.get("popularity") or 0)
    return round(score, 2)


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
    out.sort(
        key=lambda row: (
            -int((row[0] or "0").replace("-", "") or 0),
            -fb_attractiveness(row[2]),
            _placement_rank(row[2]),
            row[1],
        )
    )
    return out


def _select_with_diversity(
    pending: list[tuple[str, str, dict[str, Any], Path]],
    limit: int,
) -> list[tuple[str, str, dict[str, Any], Path]]:
    """Take top attractiveness with pillar diversity (−20 soft penalty when pillar already picked)."""
    if limit <= 0:
        return pending
    from hk_city.growth_formats import is_growth_format

    remaining = list(pending)
    picked: list[tuple[str, str, dict[str, Any], Path]] = []
    pillars: dict[str, int] = {}
    growth_count = 0
    while remaining and len(picked) < limit:
        best_i = 0
        best_score = float("-inf")
        for i, row in enumerate(remaining):
            pillar = (row[2].get("pillar") or "city").lower()
            fmt = (row[2].get("format") or "").lower()
            adj = fb_attractiveness(row[2])
            if pillars.get(pillar, 0) >= 1:
                adj -= 20  # avoid same-pillar flood in top N
            # Soft cap: at most one growth-format post per FB slot
            if is_growth_format(fmt) and growth_count >= 1:
                adj -= 40
            if adj > best_score:
                best_score = adj
                best_i = i
        chosen = remaining.pop(best_i)
        picked.append(chosen)
        pillar = (chosen[2].get("pillar") or "city").lower()
        pillars[pillar] = pillars.get(pillar, 0) + 1
        if is_growth_format((chosen[2].get("format") or "").lower()):
            growth_count += 1
    # Auto-assign a1/a2 when unset so desk + FB stay aligned
    for i, (_day, _slug, meta, js) in enumerate(picked[:2]):
        want = "a1" if i == 0 else "a2"
        if not (meta.get("placement") or "").strip():
            meta["placement"] = want
            try:
                js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
    return picked


def _graph_upload_unpublished(page_id: str, token: str, image_path: Path) -> str:
    with image_path.open("rb") as fh:
        resp = requests.post(
            f"{GRAPH}/{page_id}/photos",
            data={
                "published": "false",
                "access_token": token,
            },
            files={"source": (image_path.name, fh, "image/jpeg")},
            timeout=90,
        )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not data.get("id"):
        raise RuntimeError(f"Facebook unpublished photo error {resp.status_code}: {data}")
    return str(data["id"])


def _graph_hybrid(
    page_id: str,
    token: str,
    *,
    message: str,
    link: str,
    media_fbid: str,
) -> str:
    resp = requests.post(
        f"{GRAPH}/{page_id}/feed",
        data={
            "message": message,
            "link": link,
            "attached_media": json.dumps([{"media_fbid": media_fbid}]),
            "access_token": token,
        },
        timeout=60,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not data.get("id"):
        raise RuntimeError(f"Facebook hybrid feed error {resp.status_code}: {data}")
    return str(data["id"])


def _graph_photo(page_id: str, token: str, *, message: str, image_path: Path) -> str:
    with image_path.open("rb") as fh:
        resp = requests.post(
            f"{GRAPH}/{page_id}/photos",
            data={
                "message": message,
                "access_token": token,
            },
            files={"source": (image_path.name, fh, "image/jpeg")},
            timeout=90,
        )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400 or not (data.get("id") or data.get("post_id")):
        raise RuntimeError(f"Facebook Graph error {resp.status_code}: {data}")
    return str(data.get("post_id") or data["id"])


def _graph_link(page_id: str, token: str, *, message: str, link: str) -> str:
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
    # Keep caption readable; URL still attached via Graph `link` on hybrid/link modes
    if url not in message and "http" not in message:
        message = f"{message}\n\n{url}" if message else url

    callout: Path | None = None
    skip_overlay = bool((meta.get("facebook") or {}).get("skip_overlay"))
    try:
        callout = compose_for_draft(day, meta)
        skip_overlay = bool((meta.get("facebook") or {}).get("skip_overlay"))
    except Exception as exc:
        logger.warning("FB callout compose failed for %s: %s", slug, exc)

    mode = "link"
    post_id: str
    if callout and callout.is_file() and not skip_overlay:
        try:
            media_id = _graph_upload_unpublished(page_id, token, callout)
            post_id = _graph_hybrid(
                page_id, token, message=message, link=url, media_fbid=media_id
            )
            mode = "hybrid"
        except Exception as exc:
            logger.warning("FB hybrid failed for %s (%s); trying share/photo fallback", slug, exc)
            # Fallback 1: link to /share page (OG can prefer callout when wired)
            try:
                post_id = _graph_link(page_id, token, message=message, link=share_url(slug))
                mode = "link_share"
            except Exception:
                post_id = _graph_photo(page_id, token, message=message, image_path=callout)
                mode = "photo"
    elif skip_overlay:
        post_id = _graph_link(page_id, token, message=message, link=url)
        mode = "hybrid_no_overlay"
    else:
        post_id = _graph_link(page_id, token, message=message, link=url)
        mode = "link"

    fb = dict(meta.get("facebook") or {})
    fb["post_id"] = post_id
    fb["posted_at"] = datetime.now(timezone.utc).isoformat()
    fb["link"] = url
    fb["post_mode"] = mode
    fb["attractiveness"] = fb_attractiveness(meta)
    if callout:
        fb["callout_path"] = str(callout)
    meta["facebook"] = fb
    meta["facebook_post_id"] = post_id
    js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Facebook posted %s -> %s (%s attract=%.1f)", slug, post_id, mode, fb["attractiveness"])
    return {"ok": True, "slug": slug, "post_id": post_id, "url": url, "mode": mode}


def post_pending(
    *,
    limit: int | None = None,
    lookback_days: int | None = None,
    slot: str | None = None,
) -> dict[str, Any]:
    """Post approved stories not yet on Facebook.

    Default: attractiveness-ranked quota for the current HKT daypart
    (morning 3 / noon 3 / evening 4 → 10/day across the three crons).
    Explicit ``limit`` wins. ``FACEBOOK_MAX_PER_RUN`` overrides the slot
    quota when set to a positive int. Empty / unset / 0 → use slot quota
    (never flood from env; use ``--limit 0`` only for intentional flood).
    """
    load_env()
    creds = _creds()
    if not creds:
        logger.info("Facebook skipped; FACEBOOK_PAGE_ID / FACEBOOK_PAGE_ACCESS_TOKEN not set")
        return {"ok": False, "skipped": "no_credentials", "posted": 0}

    slot_name, slot_quota = fb_slot_quota(slot)
    if limit is None:
        raw = (os.getenv("FACEBOOK_MAX_PER_RUN") or "").strip()
        if raw.isdigit() and int(raw) > 0:
            limit = int(raw)
        else:
            limit = slot_quota
    if lookback_days is None:
        lookback_days = int(os.getenv("FACEBOOK_LOOKBACK_DAYS", "14"))

    pending_all = pending_approved(lookback_days=lookback_days)
    pending = _select_with_diversity(pending_all, limit if limit > 0 else len(pending_all))
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
            if "code': 190" in reason or "Session has expired" in reason or "Error validating access token" in reason:
                auth_dead = True

    posted = sum(1 for r in results if r.get("ok"))
    summary = {
        "ok": True,
        "posted": posted,
        "attempted": len(results),
        "pending_left": max(0, len(pending_approved(lookback_days=lookback_days)) - posted),
        "cap": limit,
        "slot": slot_name,
        "slot_quota": slot_quota,
        "public_base": _public_base(),
        "auth_error": auth_dead,
        "results": results,
    }
    logger.info(
        "Facebook batch %s",
        {
            k: summary[k]
            for k in ("posted", "attempted", "pending_left", "cap", "slot", "slot_quota", "public_base", "auth_error")
        },
    )
    return summary
