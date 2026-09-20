"""Rewrite a draft's hero or body from the review portal. Does not publish."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import images, llm
from common.config import load_topic_config
from common.storage import TopicStorage
from hk_city.reporter import (
    CityFlyReporter,
    _cjk_len,
    _ensure_source_footer,
    _first_heading,
    _inject_hero,
    _standfirst,
)

DRAFTS = ROOT / "hk_city" / "data" / "drafts"
AI_CREDIT = "圖：編輯部示意圖，非工程實景或官方走線。"


def _paths(day: str, slug: str) -> tuple[Path, Path]:
    folder = DRAFTS / day
    return folder / f"{slug}.md", folder / f"{slug}.json"


def _load(day: str, slug: str) -> tuple[str, dict[str, Any], Path, Path]:
    md, js = _paths(day, slug)
    if not md.exists() or not js.exists():
        raise FileNotFoundError(f"{day}/{slug}")
    meta = json.loads(js.read_text(encoding="utf-8"))
    return md.read_text(encoding="utf-8"), meta, md, js


def _save(md: Path, js: Path, raw: str, meta: dict[str, Any]) -> None:
    md.write_text(raw if raw.endswith("\n") else raw + "\n", encoding="utf-8")
    js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _strip_hero(raw: str) -> str:
    lines = raw.splitlines()
    out: list[str] = []
    for line in lines:
        if line.startswith("![") and "images/" in line:
            continue
        if line.startswith("*圖") and line.endswith("*"):
            continue
        out.append(line)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def _title_dek(raw: str, meta: dict[str, Any]) -> tuple[str, str]:
    title = meta.get("headline") or ""
    if not title:
        for line in raw.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
    dek = (meta.get("web") or {}).get("excerpt") or _standfirst(raw)
    return title, dek or ""


def regen_image(day: str, slug: str) -> dict[str, Any]:
    raw, meta, md, js = _load(day, slug)
    title, dek = _title_dek(raw, meta)
    dest = DRAFTS / day / "images" / f"{slug}.png"
    prompt = (
        f"Hong Kong city-change magazine hero. Topic: {title}. "
        f"{dek} "
        "Wide 16:9 editorial illustration, not a photograph, not an official map. "
        "Constructive, forward-looking civic energy. "
        "CRITICAL: absolutely no text, no Chinese characters, no English words, "
        "no numbers, no logos, no watermarks, no readable signage."
    )
    if not images.available():
        raise RuntimeError("未設定 KIE_API_KEY，唔能夠重畫圖。")
    hero = images.generate_illustration(prompt, dest)
    rel = f"images/{dest.name}"
    body = _inject_hero(_strip_hero(raw), rel, credit=AI_CREDIT)
    meta["hero"] = hero
    meta["needs_visual"] = None
    meta["facebook"] = meta.get("facebook") or {}
    meta["facebook"]["visual_thesis"] = f"示意圖：{title}"
    _save(md, js, body, meta)
    return {"ok": True, "kind": "image", "path": str(dest)}


def regen_text(day: str, slug: str) -> dict[str, Any]:
    if not llm.available():
        raise RuntimeError("未設定 LLM key，唔能夠重寫稿。")
    raw, meta, md, js = _load(day, slug)
    title, dek = _title_dek(raw, meta)
    sources = meta.get("sources") or []
    cand = {
        "hook": title,
        "dek": dek,
        "title": title,
        "pillar": meta.get("pillar"),
        "format": meta.get("format"),
        "district": meta.get("district"),
        "summary": (sources[0].get("summary") if sources else "") or "",
        "link": (sources[0].get("url") if sources else "") or "",
    }
    cfg = load_topic_config("hk_city")
    reporter = CityFlyReporter(TopicStorage("hk_city", as_of=day), cfg)
    body = reporter._draft_article(cand, {}, sources)
    body = _ensure_source_footer(body, sources)
    old_hero = meta.get("hero") or {}
    if old_hero.get("ok") and old_hero.get("path") and Path(old_hero["path"]).exists():
        rel = f"images/{Path(old_hero['path']).name}"
        credit = None if old_hero.get("ai_generated") else f"圖：來源附圖。{old_hero.get('credit') or ''}".strip()
        if old_hero.get("ai_generated"):
            credit = AI_CREDIT
        body = _inject_hero(_strip_hero(body), rel, credit=credit)
    n = _cjk_len(body)
    if n < 700 or n > 1080:
        raise RuntimeError(f"重寫後字數唔啱：{n}")
    meta["headline"] = _first_heading(body) or title
    meta["web"] = {
        "excerpt": dek or _standfirst(body),
        "og_title": meta["headline"],
        "og_description": dek or _standfirst(body),
    }
    _save(md, js, body, meta)
    return {"ok": True, "kind": "text", "cjk": n}
