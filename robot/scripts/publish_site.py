#!/usr/bin/env python3
"""Export approved desk drafts into web/ for the City Sight magazine."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent
WEB = REPO / "web"
DRAFTS = ROOT / "hk_city" / "data" / "drafts"

PILLAR_ORDER = ["property", "tech", "city", "mobility", "economy"]
PILLAR_LABELS = {
    "property": "樓市與生活",
    "tech": "科技改變生活",
    "city": "城市大變身",
    "mobility": "基建與交通",
    "economy": "經濟、錢與機會",
}


def _standfirst(body: str) -> str:
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("!") or s.startswith("*"):
            if lines:
                break
            continue
        if s.startswith("##"):
            break
        lines.append(s)
        if len("".join(lines)) > 80:
            break
    return " ".join(lines)[:160]


def _body_without_hero(md: str) -> str:
    text = re.sub(r"^!\[[^\]]*\]\([^)]+\)\s*\n?", "", md, count=1, flags=re.M)
    text = re.sub(r"^\*[^*]+\*\s*\n?", "", text, count=1, flags=re.M)
    return text.strip()


def _resolve_hero(day_dir: Path, meta: dict[str, Any]) -> Path | None:
    hero = meta.get("hero") or {}
    slug = str(meta.get("slug") or "")
    candidates: list[Path | None] = []

    if hero.get("ok"):
        raw = hero.get("path") or ""
        name = Path(str(raw)).name
        candidates.extend(
            [
                day_dir / "images" / name,
                day_dir / name,
                Path(raw) if raw else None,
            ]
        )
        # After repo split, absolute paths may still point at old hk_city/
        if raw and "/hk_city/" in str(raw) and "/robot/" not in str(raw):
            candidates.append(ROOT / "hk_city" / str(raw).split("/hk_city/", 1)[-1])

    # Fallback: any file named after the slug in images/
    if slug:
        images = day_dir / "images"
        if images.is_dir():
            for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                candidates.append(images / f"{slug}{ext}")
            candidates.extend(sorted(images.glob(f"{slug}.*")))

    # Markdown ![hero](images/...) reference
    md_path = day_dir / f"{slug}.md"
    if md_path.is_file():
        m = re.search(r"!\[[^\]]*\]\((images/[^)]+)\)", md_path.read_text(encoding="utf-8"))
        if m:
            candidates.append(day_dir / m.group(1))

    seen: set[str] = set()
    for c in candidates:
        if not c:
            continue
        key = str(c.resolve()) if c.exists() else str(c)
        if key in seen:
            continue
        seen.add(key)
        if c.is_file():
            return c
    return None


def _load_approved(day: str | None) -> list[dict[str, Any]]:
    days = [DRAFTS / day] if day else sorted(p for p in DRAFTS.iterdir() if p.is_dir())
    out: list[dict[str, Any]] = []
    for day_dir in days:
        if not day_dir.is_dir():
            continue
        for js in sorted(day_dir.glob("*.json")):
            meta = json.loads(js.read_text(encoding="utf-8"))
            if meta.get("status") != "approved":
                continue
            md_path = day_dir / f"{js.stem}.md"
            if not md_path.exists():
                continue
            body = md_path.read_text(encoding="utf-8")
            web = meta.get("web") or {}
            headline = meta.get("headline") or web.get("og_title") or js.stem
            dek = web.get("excerpt") or web.get("og_description") or _standfirst(body)
            out.append(
                {
                    "slug": meta.get("slug") or js.stem,
                    "as_of": meta.get("as_of") or day_dir.name,
                    "pillar": meta.get("pillar") or "city",
                    "headline": headline,
                    "dek": dek,
                    "placement": (meta.get("placement") or "").lower(),
                    "popularity": float(meta.get("popularity") or meta.get("score") or 0),
                    "body_md": _body_without_hero(body),
                    "og_title": web.get("og_title") or headline,
                    "og_description": web.get("og_description") or dek,
                    "disclaimer_required": bool(meta.get("disclaimer_required")),
                    "sources": meta.get("sources") or [],
                    "_day_dir": day_dir,
                    "_meta": meta,
                    "_hero_src": _resolve_hero(day_dir, meta),
                }
            )
    return out


def _pick_edition(stories: list[dict[str, Any]], date: str) -> dict[str, Any]:
    day = [s for s in stories if s["as_of"] == date]
    day_sorted = sorted(day, key=lambda s: (-s["popularity"], s["slug"]))

    a1 = next((s for s in day_sorted if s["placement"] == "a1"), None)
    if not a1 and day_sorted:
        # Prefer tech/city when tied on popularity
        preferred = [s for s in day_sorted if s["pillar"] in {"tech", "city"}]
        a1 = preferred[0] if preferred else day_sorted[0]

    used = {a1["slug"]} if a1 else set()
    a2: list[dict[str, Any]] = []
    a2_pillars: set[str] = set()
    if a1:
        a2_pillars.add(a1["pillar"])

    placed_a2 = [s for s in day_sorted if s["placement"] == "a2" and s["slug"] not in used]
    for s in placed_a2 + [x for x in day_sorted if x["slug"] not in used]:
        if len(a2) >= 3:
            break
        if s["slug"] in used:
            continue
        if s["pillar"] in a2_pillars and len(a2) < 3:
            # allow only if no other pillar left
            remaining = [x for x in day_sorted if x["slug"] not in used and x["pillar"] not in a2_pillars]
            if remaining:
                continue
        a2.append(s)
        used.add(s["slug"])
        a2_pillars.add(s["pillar"])

    inside: dict[str, list[str]] = {p: [] for p in PILLAR_ORDER}
    more: list[str] = []
    front_budget = 12
    front_count = (1 if a1 else 0) + len(a2)

    for s in day_sorted:
        if s["slug"] in used:
            continue
        pillar = s["pillar"] if s["pillar"] in inside else "city"
        if front_count < front_budget and len(inside[pillar]) < 2:
            inside[pillar].append(s["slug"])
            used.add(s["slug"])
            front_count += 1
        else:
            more.append(s["slug"])
            used.add(s["slug"])

    return {
        "date": date,
        "a1": a1["slug"] if a1 else None,
        "a2": [s["slug"] for s in a2],
        "inside": {p: inside[p] for p in PILLAR_ORDER if inside[p]},
        "more": more,
        "pillar_labels": PILLAR_LABELS,
    }


def publish(day: str | None = None) -> dict[str, Any]:
    approved = _load_approved(day)
    if not approved:
        raise SystemExit("No approved drafts found.")

    heroes_dir = WEB / "public" / "heroes"
    content_dir = WEB / "content"
    heroes_dir.mkdir(parents=True, exist_ok=True)
    content_dir.mkdir(parents=True, exist_ok=True)

    stories_out: list[dict[str, Any]] = []
    for s in approved:
        hero_rel = None
        src = s["_hero_src"]
        if src:
            dest_name = f"{s['slug']}{src.suffix.lower()}"
            dest = heroes_dir / dest_name
            shutil.copy2(src, dest)
            hero_rel = f"/heroes/{dest_name}"
        stories_out.append(
            {
                "slug": s["slug"],
                "as_of": s["as_of"],
                "pillar": s["pillar"],
                "pillar_label": PILLAR_LABELS.get(s["pillar"], s["pillar"]),
                "headline": s["headline"],
                "dek": s["dek"],
                "placement": s["placement"],
                "hero": hero_rel,
                "body_md": s["body_md"],
                "og_title": s["og_title"],
                "og_description": s["og_description"],
                "disclaimer_required": s["disclaimer_required"],
                "sources": [
                    {"title": x.get("title"), "url": x.get("url"), "source": x.get("source")}
                    for x in s["sources"]
                    if isinstance(x, dict)
                ],
            }
        )

    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in stories_out:
        by_day[s["as_of"]].append(s)

    latest = sorted(by_day.keys())[-1]
    edition = _pick_edition(approved, latest)
    editions = {d: _pick_edition(approved, d) for d in by_day}

    (content_dir / "stories.json").write_text(
        json.dumps(stories_out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (content_dir / "edition.json").write_text(
        json.dumps(edition, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (content_dir / "editions.json").write_text(
        json.dumps(editions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "stories": len(stories_out),
        "latest_edition": latest,
        "a1": edition.get("a1"),
        "a2": edition.get("a2"),
        "more": len(edition.get("more") or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", help="Only export this YYYY-MM-DD")
    args = parser.parse_args()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    summary = publish(args.day)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
