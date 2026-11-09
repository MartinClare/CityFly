"""Automatic desk gate: reject leaks and same-day repeats, translate English titles, approve the rest."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from common.config import PROJECT_ROOT
from hk_city import ledger
from hk_city.desk import drafts_store as drafts
from hk_city.reporter import _looks_like_worksheet

logger = logging.getLogger(__name__)

CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")

HOLD_TRANSLATED = "hold_translated"


def instruction_leak(markdown: str, dek: str = "") -> bool:
    text = markdown or ""
    lead = (dek or "").strip()
    if lead.startswith(("我需要", "用户", "用戶", "We need")):
        return True
    if "我需要寫" in text or "我們需要寫" in text or "不要虛構" in text[:800]:
        return True
    return _looks_like_worksheet(text)


def english_title(text: str) -> bool:
    """True when a headline is still the English source line, not a Chinese hook."""
    raw = (text or "").strip()
    if not raw:
        return False
    cjk = len(CJK.findall(raw))
    latin = len(LATIN.findall(raw))
    if latin < 8:
        return False
    return cjk <= 2 or latin > cjk * 2


def _urls(meta: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for src in meta.get("sources") or []:
        if not isinstance(src, dict):
            continue
        key = ledger.url_key(src.get("url") or src.get("link"))
        if key:
            found.add(key)
    return found


def _title_keys(meta: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for field in ("headline", "title_source"):
        key = ledger.title_key(meta.get(field))
        if len(key) >= 8 and key not in keys:
            keys.append(key)
    return keys


def similar(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if _urls(a) & _urls(b):
        return True
    for left in _title_keys(a):
        for right in _title_keys(b):
            if left == right or SequenceMatcher(None, left, right).ratio() >= ledger.SIMILAR:
                return True
    return False


def _stamp(action: str, reason: str) -> dict[str, str]:
    return {
        "action": action,
        "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _model_gate(meta: dict[str, Any], raw: str, keepers: list[dict[str, Any]]) -> str:
    """Ask the model to read the draft. Returns leak, same, ok, or hold."""
    from common import llm

    body = re.split(r"\n## 來源", raw or "", maxsplit=1)[0][:1800]
    peers = []
    for keeper in keepers:
        urls = sorted(_urls(keeper))
        peers.append(
            {
                "slug": keeper.get("slug"),
                "headline": keeper.get("headline") or keeper.get("title_source") or "",
                "url": urls[0] if urls else "",
            }
        )
    system = "你是香港雜誌的審稿編輯。只輸出一行 JSON，不要解釋。"
    user = (
        "判斷這篇待審稿。\n"
        "leak 為 true：正文洩露寫作指示、交代寫作過程，或說明自己不能寫什麼。\n"
        "same 為 true：與下列同日稿之中任何一篇報導同一件事，即使標題不同。\n"
        "兩者皆否才可通過。\n"
        '只輸出 {"leak": false, "same": false}\n'
        f"待審標題：{meta.get('headline') or ''}\n"
        f"待審連結：{sorted(_urls(meta))[:3]}\n"
        f"待審正文：{body}\n"
        f"同日已留稿：{json.dumps(peers, ensure_ascii=False)}\n"
    )
    text = llm.chat(system, user, temperature=0, max_tokens=80)
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return "hold"
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return "hold"
    if data.get("leak") is True:
        return "leak"
    if data.get("same") is True:
        return "same"
    if data.get("leak") is False and data.get("same") is False:
        return "ok"
    return "hold"


def translate_title(title: str) -> str:
    from common import llm

    system = "你是香港雜誌編輯。只輸出一行繁體中文標題，不要解釋，不要引號，不要井號。"
    user = (
        "把這個英文新聞標題改成香港口語雜誌標題。"
        "短、具體、像封面句，不要直譯腔，不要加副題。\n"
        f"標題：{title.strip()}"
    )
    out = llm.chat(system, user, temperature=0.3, max_tokens=120).strip()
    out = out.strip("`\"'「」# ").splitlines()[0].strip()
    if out.startswith("#"):
        out = out.lstrip("#").strip()
    return out


def _replace_heading(raw: str, title: str) -> str:
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines[i] = f"# {title}"
            text = "\n".join(lines)
            return text if text.endswith("\n") else text + "\n"
    return raw


def _write_meta(js: Path, meta: dict[str, Any]) -> None:
    import json

    js.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _apply_translation(day: str, slug: str, title: str) -> None:
    raw, meta, md, js = drafts.load_pack(day, slug)
    md.write_text(_replace_heading(raw, title), encoding="utf-8")
    meta["headline"] = title
    web = meta.get("web") or {}
    web["og_title"] = title
    meta["web"] = web
    _write_meta(js, meta)


def review_day(day: str) -> dict[str, Any]:
    """Review one edition day. Only pending drafts change. Human decisions stay."""
    folder = drafts.DRAFTS / day
    if not folder.is_dir():
        return {"day": day, "approved": 0, "rejected": 0, "held": 0, "notes": []}

    slugs = sorted(p.stem for p in folder.glob("*.md"))
    keepers: list[dict[str, Any]] = []
    counts = {"approved": 0, "rejected": 0, "held": 0}
    notes: list[str] = []

    for slug in slugs:
        raw, meta, _, js = drafts.load_pack(day, slug)
        meta.setdefault("slug", slug)
        status = meta.get("status") or "draft_pending_review"
        if status != "draft_pending_review":
            if status != "rejected":
                keepers.append(meta)
            continue
        prior = meta.get("auto_review") or {}
        if prior.get("action") == HOLD_TRANSLATED:
            keepers.append(meta)
            counts["held"] += 1
            continue

        headline = (meta.get("headline") or "").strip()
        dek = ((meta.get("web") or {}).get("excerpt") or "").strip()
        from hk_city.analyzers.classify import off_brief_kind

        if off_brief_kind(headline, f"{meta.get('title_source') or ''} {dek}"):
            meta["status"] = "rejected"
            meta["auto_review"] = _stamp("rejected", "罪案、疾病或死亡新聞，不採用")
            _write_meta(js, meta)
            counts["rejected"] += 1
            notes.append(f"{slug}: 罪案疾病或死亡")
            continue

        if instruction_leak(raw, dek):
            meta["status"] = "rejected"
            meta["auto_review"] = _stamp("rejected", "指令外洩，不採用")
            _write_meta(js, meta)
            counts["rejected"] += 1
            notes.append(f"{slug}: 指令外洩")
            continue

        twin = next((k for k in keepers if similar(meta, k)), None)
        if twin:
            other = twin.get("slug") or twin.get("headline") or "同日稿"
            meta["status"] = "rejected"
            meta["auto_review"] = _stamp("rejected", f"同日相似稿，不採用（留 {other}）")
            _write_meta(js, meta)
            counts["rejected"] += 1
            notes.append(f"{slug}: 同日相似 {other}")
            continue

        if english_title(headline):
            try:
                translated = translate_title(headline)
            except Exception as exc:
                logger.exception("Title translation failed for %s", slug)
                meta["auto_review"] = _stamp("hold_translate_failed", f"英文標題翻譯失敗，請人手改：{exc}")
                _write_meta(js, meta)
                keepers.append(meta)
                counts["held"] += 1
                notes.append(f"{slug}: 翻譯失敗")
                continue
            if not translated or english_title(translated) or not CJK.search(translated):
                meta["auto_review"] = _stamp("hold_translate_failed", "英文標題翻譯失敗，請人手改")
                _write_meta(js, meta)
                keepers.append(meta)
                counts["held"] += 1
                notes.append(f"{slug}: 翻譯失敗")
                continue
            _apply_translation(day, slug, translated)
            _, meta, _, js = drafts.load_pack(day, slug)
            meta["auto_review"] = _stamp(HOLD_TRANSLATED, "來源係英文標題，已譯成中文，請審批")
            _write_meta(js, meta)
            keepers.append(meta)
            counts["held"] += 1
            notes.append(f"{slug}: 已譯標題")
            continue

        try:
            verdict = _model_gate(meta, raw, keepers)
        except Exception as exc:
            logger.exception("Model gate failed for %s", slug)
            meta["auto_review"] = _stamp("hold_model", f"模型審稿失敗，請人手審：{exc}")
            _write_meta(js, meta)
            keepers.append(meta)
            counts["held"] += 1
            notes.append(f"{slug}: 模型未完成")
            continue
        if verdict == "leak":
            meta["status"] = "rejected"
            meta["auto_review"] = _stamp("rejected", "模型判定洩露寫作指示，不採用")
            _write_meta(js, meta)
            counts["rejected"] += 1
            notes.append(f"{slug}: 模型外洩")
            continue
        if verdict == "same":
            meta["status"] = "rejected"
            meta["auto_review"] = _stamp("rejected", "模型判定與同日稿同一件事，不採用")
            _write_meta(js, meta)
            counts["rejected"] += 1
            notes.append(f"{slug}: 模型同日同一事")
            continue
        if verdict != "ok":
            meta["auto_review"] = _stamp("hold_model", "模型未能判斷，請人手審")
            _write_meta(js, meta)
            keepers.append(meta)
            counts["held"] += 1
            notes.append(f"{slug}: 留人手")
            continue

        meta["status"] = "approved"
        meta["auto_review"] = _stamp("approved", "自動通過")
        _write_meta(js, meta)
        keepers.append(meta)
        counts["approved"] += 1
        notes.append(f"{slug}: 通過")

    summary = {"day": day, **counts, "notes": notes}
    logger.info("Auto review %s", summary)
    return summary


def purge_dropped() -> dict[str, Any]:
    """Delete crime, disease, death, and instruction-leak packs, including the article file."""
    from hk_city.analyzers.classify import off_brief_kind

    removed = 0
    notes: list[str] = []
    for day in drafts.days():
        folder = drafts.DRAFTS / day
        if not folder.is_dir():
            continue
        for js in sorted(folder.glob("*.json")):
            meta = json.loads(js.read_text(encoding="utf-8"))
            slug = js.stem
            headline = (meta.get("headline") or "").strip()
            dek = ((meta.get("web") or {}).get("excerpt") or "").strip()
            reason = ((meta.get("auto_review") or {}).get("reason") or "")
            md_path = folder / f"{slug}.md"
            raw = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
            kind = off_brief_kind(headline, f"{meta.get('title_source') or ''} {dek}")
            leaked = instruction_leak(raw, dek)
            dropped = "罪案、疾病或死亡" in reason or kind in {"crime", "disease", "death"} or leaked
            if not dropped:
                continue
            drafts.delete_pack(day, slug)
            removed += 1
            why = kind or ("leak" if leaked else "dropped")
            notes.append(f"{day}/{slug}: {why} {headline}")
    summary = {"removed": removed, "notes": notes}
    logger.info("Purged dropped packs %s", summary)
    return summary


def reject_off_brief() -> dict[str, Any]:
    """Unpublish crime, disease, and death stories, including ones already approved."""
    from hk_city.analyzers.classify import off_brief_kind

    rejected = 0
    notes: list[str] = []
    for day in drafts.days():
        folder = drafts.DRAFTS / day
        if not folder.is_dir():
            continue
        for js in sorted(folder.glob("*.json")):
            meta = json.loads(js.read_text(encoding="utf-8"))
            if (meta.get("status") or "") == "rejected":
                continue
            headline = (meta.get("headline") or "").strip()
            dek = ((meta.get("web") or {}).get("excerpt") or "").strip()
            kind = off_brief_kind(headline, f"{meta.get('title_source') or ''} {dek}")
            if not kind:
                continue
            meta["status"] = "rejected"
            meta["auto_review"] = _stamp("rejected", "罪案、疾病或死亡新聞，不採用")
            _write_meta(js, meta)
            rejected += 1
            notes.append(f"{day}/{js.stem}: {kind} {headline}")
    summary = {"rejected": rejected, "notes": notes}
    logger.info("Off-brief unpublish %s", summary)
    return summary


def review_after(day: str) -> list[dict[str, Any]]:
    """Review every draft day strictly after `day` (YYYY-MM-DD)."""
    out = []
    for name in drafts.days():
        if name > day:
            out.append(review_day(name))
    return out


def export_site() -> dict[str, Any] | None:
    """Publish approved drafts to the magazine checkout (when present) and Facebook.

    On ECS the web/ tree is absent; magazine JSON is still served live from the desk
    `/published/` API that Vercel polls. Facebook posting still runs here so approve
    and daily cron stay in one path.
    """
    site_summary: dict[str, Any] | None = None
    web = PROJECT_ROOT.parent / "web"
    if (web / "package.json").is_file():
        scripts = str(PROJECT_ROOT / "scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from publish_site import publish

        try:
            site_summary = publish(None)
            logger.info("Site export %s", site_summary)
        except SystemExit:
            logger.info("Site export skipped; no approved drafts")
    else:
        logger.info("Site export skipped; %s is not the magazine checkout", web)

    fb_summary: dict[str, Any] | None = None
    try:
        from hk_city.facebook_publish import post_pending

        fb_summary = post_pending()
    except Exception as exc:
        logger.exception("Facebook publish failed: %s", exc)
        fb_summary = {"ok": False, "error": str(exc), "posted": 0}

    return {"site": site_summary, "facebook": fb_summary}
