"""Draft listing and mutation helpers for the desk portal."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common.config import PROJECT_ROOT
from hk_city import ledger

DRAFTS = PROJECT_ROOT / "hk_city" / "data" / "drafts"
CJK = re.compile(r"[\u4e00-\u9fff]")
STATUSES = {
    "draft_pending_review": "待審",
    "approved": "通過",
    "needs_edit": "要改",
    "rejected": "不採用",
}


def cjk_len(text: str) -> int:
    body = re.split(r"\n## 來源", text or "", maxsplit=1)[0]
    return len(CJK.findall(body))


def days() -> list[str]:
    if not DRAFTS.exists():
        return []
    return sorted(
        (p.name for p in DRAFTS.iterdir() if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", p.name)),
        reverse=True,
    )


def _is_worksheet(raw: str, dek: str) -> bool:
    return dek.startswith(("我需要", "用户", "We need", "![hero]")) or (
        "我需要寫" in raw or "不要虛構" in raw[:400]
    )


def packs(day: str, *, status: str | None = None, hide_worksheets: bool = True) -> list[dict[str, Any]]:
    folder = DRAFTS / day
    if not folder.exists():
        return []
    rows: list[dict[str, Any]] = []
    for md in sorted(folder.glob("*.md")):
        raw = md.read_text(encoding="utf-8")
        meta: dict[str, Any] = {}
        js = md.with_suffix(".json")
        if js.exists():
            try:
                meta = json.loads(js.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        title = meta.get("headline") or ""
        if not title:
            for line in raw.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        n = cjk_len(raw)
        if n < 700:
            band = "short"
        elif n > 1000:
            band = "long"
        else:
            band = "ok"
        hero_ok = bool((meta.get("hero") or {}).get("ok"))
        rel = None
        m = re.search(r"!\[(?:hero|[^\]]*)\]\((images/[^)]+)\)", raw)
        if m:
            rel = m.group(1)
        dek = (meta.get("web") or {}).get("excerpt") or ""
        worksheet = _is_worksheet(raw, dek)
        if hide_worksheets and worksheet:
            continue
        st = meta.get("status") or "draft_pending_review"
        if status and status != "all" and st != status:
            continue
        rows.append(
            {
                "slug": md.stem,
                "title": title or md.stem,
                "dek": "" if worksheet else dek,
                "cjk": n,
                "band": band,
                "hero": hero_ok,
                "thumb": rel,
                "status": st,
                "pillar": meta.get("pillar") or "",
                "worksheet": worksheet,
            }
        )
    return rows


def load_pack(day: str, slug: str) -> tuple[str, dict[str, Any], Path, Path]:
    md = DRAFTS / day / f"{slug}.md"
    js = md.with_suffix(".json")
    if not md.exists():
        raise FileNotFoundError(f"{day}/{slug}")
    meta: dict[str, Any] = {}
    if js.exists():
        try:
            meta = json.loads(js.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    return md.read_text(encoding="utf-8"), meta, md, js


def set_status(day: str, slug: str, status: str) -> None:
    if status not in STATUSES:
        raise ValueError("bad status")
    _, meta, _, js = load_pack(day, slug)
    meta["status"] = status
    js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def neighbors(day: str, slug: str, queue: str) -> dict[str, str | None]:
    """Prev/next article URLs within the current queue (same day first)."""
    rows = packs(day, status=None if queue == "all" else queue)
    if not rows:
        rows = packs(day)
    slugs = [r["slug"] for r in rows]
    try:
        i = slugs.index(slug)
    except ValueError:
        return {"prev": None, "next": None, "index": 0, "total": len(slugs)}
    prev_url = f"/a/{day}/{slugs[i - 1]}?queue={queue}" if i > 0 else None
    next_url = f"/a/{day}/{slugs[i + 1]}?queue={queue}" if i + 1 < len(slugs) else None
    if next_url is None:
        # try later days
        all_days = days()
        if day in all_days:
            for later in all_days[all_days.index(day) + 1 :]:
                nxt = packs(later, status=None if queue == "all" else queue)
                if nxt:
                    next_url = f"/a/{later}/{nxt[0]['slug']}?queue={queue}"
                    break
    if prev_url is None:
        all_days = days()
        if day in all_days:
            for earlier in reversed(all_days[: all_days.index(day)]):
                prev_rows = packs(earlier, status=None if queue == "all" else queue)
                if prev_rows:
                    prev_url = f"/a/{earlier}/{prev_rows[-1]['slug']}?queue={queue}"
                    break
    return {"prev": prev_url, "next": next_url, "index": i + 1, "total": len(slugs)}


def next_location(day: str, slug: str, queue: str) -> str:
    rows = packs(day, status=None, hide_worksheets=True)
    slugs = [r["slug"] for r in rows]
    try:
        start = slugs.index(slug) + 1
    except ValueError:
        start = 0
    for row in rows[start:]:
        if queue == "all" or row["status"] == queue:
            return f"/a/{day}/{row['slug']}?queue={queue}"
    all_days = days()
    if day in all_days:
        for later in all_days[all_days.index(day) + 1 :]:
            nxt = packs(later, status=None if queue == "all" else queue)
            if nxt:
                return f"/a/{later}/{nxt[0]['slug']}?queue={queue}"
    return f"/?day={day}&status={queue}"


def parse_article_parts(raw: str) -> dict[str, str]:
    title = ""
    hero_src = ""
    credit = ""
    rest: list[str] = []
    for line in raw.splitlines():
        if line.startswith("<!--"):
            continue
        if not title and line.startswith("# "):
            title = line[2:].strip()
            continue
        if not hero_src and line.startswith("![") and "images/" in line and "(" in line:
            hero_src = line[line.find("(") + 1 : line.rfind(")")]
            continue
        if not credit and line.startswith("*圖") and line.endswith("*"):
            credit = line.strip("*")
            continue
        rest.append(line)
    dek = ""
    kept: list[str] = []
    for line in rest:
        if not dek and line.strip() and not line.startswith("#") and not line.startswith("!["):
            dek = line.strip()
            continue
        kept.append(line)
    body = "\n".join(kept).strip()
    return {"title": title, "dek": dek, "hero_src": hero_src, "credit": credit, "body": body}


def rebuild_markdown(
    *,
    title: str,
    dek: str,
    body: str,
    hero_src: str = "",
    credit: str = "",
    model_line: str = "",
) -> str:
    parts: list[str] = []
    if model_line:
        parts.append(model_line.rstrip())
        parts.append("")
    parts.append(f"# {title.strip()}")
    parts.append("")
    if hero_src:
        parts.append(f"![hero]({hero_src})")
        parts.append("")
        if credit:
            parts.append(f"*{credit}*")
            parts.append("")
    if dek.strip():
        parts.append(dek.strip())
        parts.append("")
    parts.append(body.strip())
    parts.append("")
    return "\n".join(parts)


def save_edits(day: str, slug: str, *, title: str, dek: str, body: str) -> int:
    raw, meta, md, js = load_pack(day, slug)
    parts = parse_article_parts(raw)
    model_line = ""
    for line in raw.splitlines()[:3]:
        if line.startswith("<!--"):
            model_line = line
            break
    new_raw = rebuild_markdown(
        title=title or parts["title"],
        dek=dek if dek is not None else parts["dek"],
        body=body if body is not None else parts["body"],
        hero_src=parts["hero_src"],
        credit=parts["credit"],
        model_line=model_line,
    )
    n = cjk_len(new_raw)
    meta["headline"] = title.strip() or parts["title"]
    meta["web"] = meta.get("web") or {}
    meta["web"]["excerpt"] = (dek or "").strip()
    meta["web"]["og_title"] = meta["headline"]
    meta["web"]["og_description"] = (dek or "").strip()
    md.write_text(new_raw if new_raw.endswith("\n") else new_raw + "\n", encoding="utf-8")
    js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return n


def delete_pack(day: str, slug: str) -> None:
    raw, meta, md, js = load_pack(day, slug)
    hero = meta.get("hero") or {}
    hero_path = hero.get("path")
    # also from markdown
    parts = parse_article_parts(raw)
    rel = parts.get("hero_src") or ""
    images_dir = DRAFTS / day / "images"
    to_remove: list[Path] = []
    if hero_path:
        p = Path(hero_path)
        if not p.is_absolute():
            p = DRAFTS / day / p
        to_remove.append(p)
    if rel:
        to_remove.append(DRAFTS / day / rel)
    # slug-named images
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        to_remove.append(images_dir / f"{slug}{ext}")
    seen: set[Path] = set()
    for p in to_remove:
        try:
            rp = p.resolve()
        except OSError:
            continue
        if rp in seen or not rp.exists():
            continue
        # only delete under drafts images
        try:
            rp.relative_to((DRAFTS / day / "images").resolve())
        except ValueError:
            continue
        seen.add(rp)
        rp.unlink(missing_ok=True)
    item = {
        "title": meta.get("headline") or meta.get("title_source"),
        "hook": meta.get("headline"),
        "link": ((meta.get("sources") or [{}])[0] or {}).get("url"),
        "sources": meta.get("sources") or [],
    }
    ledger.forget(slug, item=item)
    md.unlink(missing_ok=True)
    js.unlink(missing_ok=True)


def md_to_html(text: str) -> str:
    import html as html_mod

    parts = parse_article_parts(text)
    out: list[str] = []
    if parts["title"]:
        out.append(f'<h1 class="topic">{_inline(parts["title"])}</h1>')
    if parts["dek"]:
        out.append(f'<p class="dek">{_inline(parts["dek"])}</p>')
    if parts["hero_src"]:
        name = Path(parts["hero_src"].split("?", 1)[0]).name
        stamp = ""
        for day in days():
            p = DRAFTS / day / "images" / name
            if p.exists():
                stamp = f"?v={int(p.stat().st_mtime)}"
                break
        out.append(f'<img class="hero" src="/images/{html_mod.escape(name)}{stamp}" alt="">')
    if parts["credit"]:
        out.append(f'<p class="credit">{_inline(parts["credit"])}</p>')

    para: list[str] = []

    def flush() -> None:
        if para:
            out.append("<p>" + " ".join(para) + "</p>")
            para.clear()

    for line in parts["body"].splitlines():
        if line.startswith("## "):
            flush()
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            flush()
            out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("- "):
            flush()
            out.append(f"<li>{_inline(line[2:])}</li>")
        elif not line.strip():
            flush()
        else:
            para.append(_inline(line))
    flush()
    return "\n".join(out)


def _inline(s: str) -> str:
    import html as html_mod

    s = html_mod.escape(s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" rel="noreferrer">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s


def health_text() -> str:
    import subprocess

    log = PROJECT_ROOT / "hk_city" / "data" / "cron.log"
    if PROJECT_ROOT.parent == Path("/opt") and (PROJECT_ROOT / "run_daily.py").exists():
        parts = [
            subprocess.getoutput("date"),
            subprocess.getoutput("uptime -p"),
            subprocess.getoutput("df -h / | tail -1"),
        ]
        cron = subprocess.getoutput("crontab -l | grep hk_city || true")
        parts.append("=== cron ===\n" + cron)
        if log.exists():
            parts.append(
                "=== log ===\n"
                + "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:])
            )
        else:
            parts.append("=== log ===\n(no cron.log yet)")
        return "\n".join(parts)
    host_env = PROJECT_ROOT / "scripts" / "alibaba" / ".state" / "host.env"
    script = PROJECT_ROOT / "scripts" / "alibaba" / "health.sh"
    if not host_env.exists() or not script.exists():
        return "本機模式。香港機健康請用 scripts/alibaba/health.sh。"
    try:
        proc = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=20)
        return (proc.stdout or "") + (proc.stderr or "") or "(empty)"
    except Exception as exc:
        return f"無法檢查：{exc}"
