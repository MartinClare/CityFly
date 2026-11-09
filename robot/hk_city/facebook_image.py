"""Facebook-only share image: gold frame + tight black text pad.

Composes a landscape 1200×630 JPEG from the draft hero for feed photos.
Never mutates the web hero file; writes a sibling `*.fb.jpg` under the
day's images folder.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Facebook feed photo — landscape, independent of web OG/hero crop
FB_W, FB_H = 1200, 630
GOLD = (232, 196, 138)  # #e8c48a
GOLD_ACCENT = (212, 163, 92)  # #d4a35c
BLACK = (12, 12, 14)
BORDER_W = 4
PAD = 10  # black panel: ~10px outside ink
GAP = 42
TITLE_SIZE = 72
SUB_SIZE = 46
MAX_TITLE = 12
MAX_SUB = 20

_BOLD_OFFS = ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2))

_FONT_BOLD = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/Users/alex/Library/Fonts/NotoSansHK-Bold.ttf",
    "/System/Library/Fonts/PingFang.ttc",
)
_FONT_REG = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/Users/alex/Library/Fonts/NotoSansHK-Bold.ttf",  # fallback if Regular missing
    "/System/Library/Fonts/PingFang.ttc",
)


def _first_font(candidates: tuple[str, ...], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        if not Path(path).exists():
            continue
        try:
            if path.endswith(".ttc"):
                return ImageFont.truetype(path, size=size, index=0)
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _cjk_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


_BREAK = set(" ，、；：:。.！？!?|/｜—–-")


def _trim(text: str, max_chars: int) -> str:
    """Trim to max non-space chars, preferring a phrase break over mid-cut."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if _cjk_len(t) <= max_chars:
        return t
    # gather candidates that end on a break char within the budget
    n = 0
    last_break = -1
    for i, ch in enumerate(t):
        if not ch.isspace():
            n += 1
        if n > max_chars:
            break
        if ch in _BREAK:
            last_break = i
    if last_break > 0:
        return t[:last_break].rstrip(" ，、；：:。.！？!?|/｜—–-")
    out: list[str] = []
    n = 0
    for ch in t:
        if ch.isspace() and not out:
            continue
        if not ch.isspace():
            if n >= max_chars:
                break
            n += 1
        out.append(ch)
    return "".join(out).rstrip(" ，、；：:。.！？!?|/｜—–-")


def _heuristic_lines(meta: dict[str, Any]) -> tuple[str, str]:
    headline = (meta.get("headline") or meta.get("title") or "").strip()
    excerpt = (
        ((meta.get("web") or {}).get("excerpt") or "")
        or (meta.get("dek") or "")
        or ((meta.get("facebook") or {}).get("visual_thesis") or "")
    ).strip()
    title, sub = "", ""
    for sep in ("：", ":", " — ", " – ", " - ", "｜", "|"):
        if sep in headline:
            left, right = headline.split(sep, 1)
            title, sub = left.strip(), right.strip()
            break
    if not title:
        # prefer first phrase before space /顿号 if that fits
        title = headline
    alt = ""
    if excerpt:
        alt = re.split(r"[。！？\n]", excerpt, maxsplit=1)[0].strip()
    if not sub:
        cap = ((meta.get("facebook") or {}).get("caption") or excerpt or "").strip()
        cap = re.split(r"\n\n", cap, maxsplit=1)[0].strip()
        sub = re.split(r"[。！？\n]", cap, maxsplit=1)[0].strip()
    if sub and _cjk_len(sub) > MAX_SUB and alt and _cjk_len(alt) <= MAX_SUB:
        sub = alt
    if not sub or sub == title:
        sub = alt or excerpt
    return _trim(title, MAX_TITLE) or "城市觀察", _trim(sub, MAX_SUB)


_CALLOUT_SYSTEM = f"""You write City Sight Facebook overlay lines in Traditional written Chinese (書面中文), not spoken Cantonese.
Return ONLY one JSON object, no markdown, no explanation.
Fields:
- title: complete hook, ≤{MAX_TITLE} non-space chars, never cut mid-word/bracket
- subtitle: complete factual line, ≤{MAX_SUB} non-space chars, never cut mid-clause
Example: {{"title":"把對話鎖進抽屜","subtitle":"ChatGPT 私隱開關改寫界線"}}"""


def _parse_callout_json(raw: str) -> tuple[str, str] | None:
    import json

    text = (raw or "").strip()
    if not text:
        return None
    m = re.search(r"\{[^{}]+\}", text, re.S)
    if m:
        try:
            data = json.loads(m.group(0))
            title = str(data.get("title") or "").strip()
            sub = str(data.get("subtitle") or "").strip()
            if title:
                return _trim(title, MAX_TITLE), _trim(sub, MAX_SUB) if sub else ""
        except json.JSONDecodeError:
            pass
    # freeform fallback: title：... / subtitle：...
    tm = re.search(r"(?:title|標題)\s*[:：]\s*[「\"']?(.+?)[」\"']?\s*(?:\n|$)", text, re.I)
    sm = re.search(r"(?:subtitle|副題|副標題)\s*[:：]\s*[「\"']?(.+?)[」\"']?\s*(?:\n|$)", text, re.I)
    if tm:
        title = tm.group(1).strip().strip("「」\"'")
        sub = sm.group(1).strip().strip("「」\"'") if sm else ""
        if title:
            return _trim(title, MAX_TITLE), _trim(sub, MAX_SUB) if sub else ""
    return None


def regenerate_callout_lines(meta: dict[str, Any]) -> tuple[str, str]:
    """LLM-write complete title/subtitle within caps; fallback to heuristic."""
    from common import llm

    headline = (meta.get("headline") or meta.get("title") or "").strip()
    excerpt = (
        ((meta.get("web") or {}).get("excerpt") or "")
        or (meta.get("dek") or "")
        or ""
    ).strip()[:240]
    user = (
        f"headline: {headline}\n"
        f"excerpt: {excerpt}\n"
        f'Return only: {{"title":"...","subtitle":"..."}}'
    )
    if llm.available():
        try:
            raw = llm.chat(
                _CALLOUT_SYSTEM,
                user,
                temperature=0.2,
                max_tokens=1536,
                reasoning_effort="low",
            )
            parsed = _parse_callout_json(raw)
            if parsed and parsed[0]:
                return parsed
            logger.warning("FB callout LLM parse failed: %s", (raw or "")[:160])
        except Exception as exc:
            logger.warning("FB callout LLM failed: %s", exc)
    return _heuristic_lines(meta)


def callout_lines(meta: dict[str, Any], *, prefer_cached: bool = True) -> tuple[str, str]:
    """Hook + subtitle for the FB overlay (≤12 / ≤20 chars)."""
    fb = meta.get("facebook") or {}
    if prefer_cached:
        cached_t = (fb.get("callout_title") or "").strip()
        cached_s = (fb.get("callout_subtitle") or "").strip()
        if cached_t:
            return _trim(cached_t, MAX_TITLE), _trim(cached_s, MAX_SUB) if cached_s else ""
    return _heuristic_lines(meta)


def apply_callout_lines(meta: dict[str, Any], title: str, subtitle: str) -> dict[str, Any]:
    fb = dict(meta.get("facebook") or {})
    fb["callout_title"] = title
    fb["callout_subtitle"] = subtitle
    meta["facebook"] = fb
    return meta


def resolve_hero_path(day: str, meta: dict[str, Any], *, drafts_root: Path | None = None) -> Path | None:
    from hk_city.desk.drafts_store import DRAFTS

    root = drafts_root or DRAFTS
    day_dir = root / day
    hero = meta.get("hero") or {}
    slug = str(meta.get("slug") or "")
    candidates: list[Path] = []
    if hero.get("ok"):
        raw = str(hero.get("path") or "")
        name = Path(raw).name
        if name:
            candidates.append(day_dir / "images" / name)
            candidates.append(day_dir / name)
        if raw:
            candidates.append(Path(raw))
    if slug:
        images = day_dir / "images"
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidates.append(images / f"{slug}{ext}")
    for p in candidates:
        try:
            if p.is_file() and not p.name.endswith(".fb.jpg"):
                return p
        except OSError:
            continue
    return None


def fb_callout_path(hero: Path) -> Path:
    """Sibling path for the FB-only JPEG (never the web hero name)."""
    return hero.with_name(hero.stem + ".fb.jpg")


def _cover_resize(img: Image.Image, w: int, h: int) -> Image.Image:
    src = img.convert("RGB")
    sw, sh = src.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    src = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return src.crop((left, top, left + w, top + h))


def _ink_bbox(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    *,
    bold: bool = False,
) -> tuple[int, int, int, int]:
    x, y = xy
    offs = _BOLD_OFFS if bold else ((0, 0),)
    boxes = [draw.textbbox((x + dx, y + dy), text, font=font) for dx, dy in offs]
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _band_edge_density(img: Image.Image, y0: float, y1: float) -> float:
    """Rough text/chrome busy score via luminance edge density in a vertical band."""
    rgb = img.convert("L")
    w, h = rgb.size
    top = max(0, int(h * y0))
    bot = min(h, int(h * y1))
    if bot <= top + 2 or w < 4:
        return 0.0
    crop = rgb.crop((0, top, w, bot))
    pix = crop.load()
    cw, ch = crop.size
    edges = 0
    samples = 0
    step = max(1, min(cw, ch) // 120)
    for y in range(1, ch, step):
        for x in range(1, cw, step):
            samples += 1
            dx = abs(pix[x, y] - pix[x - 1, y])
            dy = abs(pix[x, y] - pix[x, y - 1])
            if dx + dy > 48:
                edges += 1
    return (edges / samples) if samples else 0.0


def hero_busy_scores(hero_path: Path) -> dict[str, float]:
    """Top/bottom busy scores for quiet-zone placement."""
    try:
        img = Image.open(hero_path)
        fitted = _cover_resize(img, FB_W, FB_H)
    except OSError:
        return {"top": 0.0, "bottom": 0.0, "max": 0.0}
    top = _band_edge_density(fitted, 0.0, 0.33)
    bottom = _band_edge_density(fitted, 0.67, 1.0)
    return {"top": top, "bottom": bottom, "max": max(top, bottom)}


def looks_text_heavy(hero_path: Path, meta: dict[str, Any] | None = None) -> bool:
    """True when lower/upper band looks like baked-in captions or UI chrome."""
    hero_meta = (meta or {}).get("hero") or {}
    if hero_meta.get("ai_generated"):
        return False
    scores = hero_busy_scores(hero_path)
    if scores["max"] >= 0.22:
        return True
    # Tall/narrow screenshots often carry UI chrome
    try:
        with Image.open(hero_path) as im:
            w, h = im.size
        if h > 0 and w / h < 1.15 and scores["max"] >= 0.14:
            return True
    except OSError:
        pass
    return False


def _maybe_ai_fb_base(day: str, meta: dict[str, Any], hero: Path) -> Path:
    """If web hero is text-heavy, generate a FB-only AI base (never overwrite web hero)."""
    if not looks_text_heavy(hero, meta):
        return hero
    from common import images as img_mod

    if not img_mod.available():
        return hero
    slug = str(meta.get("slug") or hero.stem)
    dest = hero.with_name(f"{slug}.fb-base.png")
    if dest.is_file() and dest.stat().st_size > 20_000:
        return dest
    prompt = (
        f"Topic: {meta.get('headline') or meta.get('title') or slug}. "
        f"Pillar: {meta.get('pillar') or 'city'}. "
        "Clean conceptual illustration with NO readable text, NO UI chrome, NO captions, NO watermarks."
    )
    try:
        result = img_mod.generate_illustration(prompt, dest)
        if result.get("ok") and Path(result["path"]).is_file():
            logger.info("FB AI base for text-heavy hero -> %s", result["path"])
            return Path(result["path"])
    except Exception as exc:
        logger.warning("FB AI base failed for %s: %s", slug, exc)
    return hero


def compose_callout(
    hero_path: Path,
    title: str,
    subtitle: str,
    *,
    out_path: Path | None = None,
    pad_top: bool | None = None,
) -> Path:
    """Render FB share image; writes `*.fb.jpg` beside the hero by default."""
    dest = out_path or fb_callout_path(hero_path)
    if dest.resolve() == hero_path.resolve():
        raise ValueError("Refusing to overwrite web hero with FB callout")

    base = _cover_resize(Image.open(hero_path), FB_W, FB_H)
    scores = hero_busy_scores(hero_path)
    if pad_top is None:
        # Prefer quieter edge; default bottom
        pad_top = scores["bottom"] > scores["top"] + 0.04

    overlay = Image.new("RGBA", (FB_W, FB_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    if pad_top:
        for y in range(0, int(FB_H * 0.42)):
            a = int(100 * (1 - y / (FB_H * 0.42)))
            od.line([(0, y), (FB_W, y)], fill=(0, 0, 0, a))
    else:
        for y in range(int(FB_H * 0.45), FB_H):
            a = int(100 * (y - FB_H * 0.45) / (FB_H * 0.55))
            od.line([(0, y), (FB_W, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    f_title = _first_font(_FONT_BOLD, TITLE_SIZE)
    f_sub = _first_font(_FONT_REG, SUB_SIZE)
    margin = BORDER_W + 22

    title_draw = (0, 0)
    b1 = _ink_bbox(draw, title_draw, title, f_title, bold=True)
    th1 = b1[3] - b1[1]
    sub_draw = (0, th1 + GAP)
    b2 = _ink_bbox(draw, sub_draw, subtitle, f_sub, bold=False) if subtitle else b1
    ux0 = min(b1[0], b2[0])
    uy0 = min(b1[1], b2[1])
    ux1 = max(b1[2], b2[2])
    uy1 = max(b1[3], b2[3])

    box_w = (ux1 - ux0) + PAD * 2
    box_h = (uy1 - uy0) + PAD * 2
    x0 = margin
    if pad_top:
        y0 = margin
        y1 = y0 + box_h
    else:
        y1 = FB_H - margin
        y0 = y1 - box_h
    x1 = x0 + box_w
    ox = x0 + PAD - ux0
    oy = y0 + PAD - uy0

    draw.rectangle([x0, y0, x1, y1], fill=BLACK)

    tx, ty = ox + title_draw[0], oy + title_draw[1]
    for dx, dy in _BOLD_OFFS:
        draw.text((tx + dx, ty + dy), title, font=f_title, fill=GOLD)
    if subtitle:
        draw.text((ox + sub_draw[0], oy + sub_draw[1]), subtitle, font=f_sub, fill=GOLD)

    draw.rectangle([0, 0, FB_W - 1, FB_H - 1], outline=GOLD_ACCENT, width=BORDER_W)

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="JPEG", quality=92)
    logger.info("FB callout wrote %s (%dx%d) pad_top=%s", dest, FB_W, FB_H, pad_top)
    return dest


def compose_for_draft(
    day: str,
    meta: dict[str, Any],
    *,
    drafts_root: Path | None = None,
    regen: bool = False,
) -> Path | None:
    """Build FB callout for a draft meta. Returns path or None if no hero / skip overlay."""
    hero = resolve_hero_path(day, meta, drafts_root=drafts_root)
    if not hero:
        logger.warning("FB callout skipped; no hero for %s", meta.get("slug"))
        return None

    fb = dict(meta.get("facebook") or {})
    base = _maybe_ai_fb_base(day, meta, hero)
    # Still extreme after AI attempt → skip overlay (hybrid link uses web OG)
    if looks_text_heavy(base, meta) and base.resolve() == hero.resolve():
        scores = hero_busy_scores(hero)
        if scores["max"] >= 0.28:
            fb["skip_overlay"] = True
            meta["facebook"] = fb
            logger.info("FB skip overlay; text-heavy hero %s busy=%.2f", hero.name, scores["max"])
            return None
    fb.pop("skip_overlay", None)

    if regen or not (fb.get("callout_title") or "").strip():
        title, subtitle = regenerate_callout_lines(meta)
        apply_callout_lines(meta, title, subtitle)
        fb = dict(meta.get("facebook") or {})
    else:
        title, subtitle = callout_lines(meta)

    out = fb_callout_path(hero)
    return compose_callout(base, title, subtitle, out_path=out)
