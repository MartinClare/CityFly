"""Persistent story memory so hourly cron does not redraft the same piece."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from common.config import data_root

LEDGER_PATH = data_root("hk_city") / "ledger" / "stories.json"
TITLE_LOOKBACK_DAYS = 21
SIMILAR = 0.86


def _lookback_days() -> int:
    try:
        from common.config import load_topic_config

        days = int(load_topic_config("hk_city").get("ledger_lookback_days") or TITLE_LOOKBACK_DAYS)
        return max(7, days)
    except Exception:
        return TITLE_LOOKBACK_DAYS


def ledger_path() -> Path:
    return LEDGER_PATH


def load() -> dict[str, Any]:
    path = ledger_path()
    if not path.exists():
        return {"stories": []}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("stories"), list):
        return {"stories": []}
    return data


def save(data: dict[str, Any]) -> Path:
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def url_key(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    path = (parsed.netloc + parsed.path).rstrip("/").lower()
    if parsed.query:
        path += "?" + parsed.query.lower()
    return path or None


def title_key(title: str | None) -> str:
    text = re.sub(r"\s+", "", (title or "").lower())
    return re.sub(r"[^\w\u4e00-\u9fff]", "", text)


def fingerprints(item: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    uk = url_key(item.get("link") or item.get("url"))
    if uk:
        keys.append("url:" + uk)
    tk = title_key(item.get("title") or item.get("hook"))
    if len(tk) >= 8:
        keys.append("t:" + tk)
    for src in item.get("sources") or []:
        suk = url_key(src.get("link") or src.get("url"))
        if suk:
            keys.append("url:" + suk)
        stk = title_key(src.get("title"))
        if len(stk) >= 8:
            keys.append("t:" + stk)
    # unique
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _match(data: dict[str, Any], item: dict[str, Any], today: str | None) -> dict[str, Any] | None:
    today_d = date.fromisoformat(today) if today else date.today()
    cutoff = today_d - timedelta(days=_lookback_days())
    fps = set(fingerprints(item))
    title = title_key(item.get("title") or item.get("hook"))
    for row in data.get("stories") or []:
        row_fps = set(row.get("fingerprints") or [])
        if fps & row_fps:
            return row
        drafted = _parse_day(row.get("drafted_on") or row.get("first_seen"))
        if drafted and drafted < cutoff:
            continue
        other = (row.get("title_key") or "")
        if title and other and len(title) >= 10 and SequenceMatcher(None, title, other).ratio() >= SIMILAR:
            return row
    return None


def is_seen(item: dict[str, Any], *, today: str | None = None) -> dict[str, Any] | None:
    """Return the matching ledger row, or None if this is a new story."""
    return _match(load(), item, today)


def mark(
    item: dict[str, Any],
    *,
    slug: str,
    status: str = "drafted",
    as_of: str | None = None,
) -> dict[str, Any]:
    data = load()
    now = as_of or date.today().isoformat()
    fps = fingerprints(item)
    existing = _match(data, item, as_of)
    if existing:
        existing["last_seen"] = now
        existing["status"] = status
        existing["slug"] = slug
        existing["fingerprints"] = sorted(set((existing.get("fingerprints") or []) + fps))
        save(data)
        return existing
    row = {
        "fingerprints": fps,
        "title_key": title_key(item.get("title") or item.get("hook")),
        "title": item.get("hook") or item.get("title"),
        "link": item.get("link") or item.get("url"),
        "first_seen": now,
        "last_seen": now,
        "drafted_on": now,
        "slug": slug,
        "status": status,
    }
    data["stories"].append(row)
    save(data)
    return row


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def forget(slug: str | None = None, *, item: dict[str, Any] | None = None) -> int:
    """Remove ledger rows matching a draft slug and/or story fingerprints."""
    data = load()
    stories = data.get("stories") or []
    if not stories:
        return 0
    drop_fps: set[str] = set()
    if item:
        drop_fps = set(fingerprints(item))
    kept: list[dict[str, Any]] = []
    removed = 0
    for row in stories:
        hit = False
        if slug and row.get("slug") == slug:
            hit = True
        if drop_fps and drop_fps & set(row.get("fingerprints") or []):
            hit = True
        if hit:
            removed += 1
            continue
        kept.append(row)
    if removed:
        data["stories"] = kept
        save(data)
    return removed


def seed_from_drafts(drafts_root: Path, as_of: str) -> int:
    """Register already-written packs so a later cron does not redo them."""
    count = 0
    if not drafts_root.exists():
        return 0
    for path in drafts_root.glob("*/*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        srcs = payload.get("sources") or []
        first = srcs[0] if srcs else {}
        item = {
            "title": payload.get("headline") or payload.get("title_source"),
            "hook": payload.get("headline"),
            "link": first.get("url") or first.get("link"),
            "sources": srcs,
        }
        if is_seen(item, today=as_of):
            continue
        mark(item, slug=payload.get("slug") or path.stem, status="drafted", as_of=as_of)
        count += 1
    return count
