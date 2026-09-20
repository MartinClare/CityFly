"""Playbook v2 reporter: daily briefing + Unwire-style article packs."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from common import images, llm
from common.base_reporter import BaseReporter
from common.config import get_llm_config
from hk_city import ledger

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "本文只作新聞、教育及一般資訊用途，不構成投資、置業、法律、按揭或財務建議。"
    "讀者應按自身情況尋求合資格專業人士意見。"
)

BRIEFING_SYSTEM = """你是香港城市變化雜誌 City Fly 的日報主編。獨立雜誌，不是政府公報，不是怨氣專欄。

讀者要帶走：新技術點改生活、生意／投資觀察／建造三個窗口、可能威脅、未證實但有趣的傳聞。

規則：
1. 以 JSON 裡的 independent_summary 與 ranked_candidates 為獨立判斷，不要只覆述頭條。
2. 用香港口語繁體（廣東話寫法）。英文只在香港人慣用英文講嘅詞先用，例如 AI、WeChat、CCL。標題向前看。
3. 不要用「根據 XX 發表」開頭。不要寫成 news.gov.hk。不要讚政策惠民、遠見、成功。
4. 本地新聞可作角度與傳聞；事實必須標明層級。傳聞寫「未證實／可能性」。
5. 地圖可以畫投資與建造窗口，但不要叫人買、賣、租、入市。不要「必升」「最啱你」。
6. 優先寫：生活會點變、科技、威脅、傳聞。路政署招標／簽約若只是公文，放監察，不要當頭條。
7. Markdown 標題：
   # 城市變化日報
   ## 今日獨立判斷
   ## 值得寫的候選
   ## 生意／投資觀察／建造
   ## 生活、科技與威脅
   ## 傳聞（未證實）
   ## 先監察
   ## 數字
   ## 明日要盯
"""

ARTICLE_SYSTEM = """你是 City Fly 的雜誌撰稿。聲線接近 Bloomberg CityLab / The Atlantic：冷靜、具體；文字用香港口語繁體（廣東話寫法）。英文只在香港人慣用英文講嘅詞先用，例如 AI、WeChat、CCL、location。

只寫稿。不要寫編輯室、研究過程、或你為什麼這樣寫。

不准：
- 發明人名、對話、街道場面、星期二早上
- 發明數字、日期、未見於來源的傳聞
- 在正文解釋「來源沒有」「現有材料睇唔到」「本文不寫」「故不採用」「按現有材料推想」「來源撐得住」「這是宣稱不是結論」「下一步要核對的文件」
- 讚政策；叫人買、賣、租、入市

來源沒有的細節，略過。不要向讀者交代你略過了什麼。
官員怎麼說，就寫他怎麼說。讀者自己判斷。

結構：
1. 一句 dek，不要印 Standfirst
2. 用來源裡的人、地、數、決定開頭
3. 正文 700–1000 字（只計中文字）。Facebook／網頁一篇這個長度。少過 700 字就未完。最多 3 個為此篇新造的小標題
4. 文末 ## 來源 + 指定免責聲明
"""

MIN_ARTICLE_CJK = 700
MAX_ARTICLE_CJK = 1000


class CityFlyReporter(BaseReporter):
    name = "hk_city_reporter"

    def build_prompt(self, view: dict[str, Any], raw: dict[str, Any]) -> tuple[str, str]:
        user = (
            "用繁體中文寫今日城市變化日報。independent_summary 是結論。"
            "先寫生活／科技／三個機會窗口；公文招標放監察。傳聞標未證實。\n\n"
            f"```json\n{json.dumps(_briefing_context(view), ensure_ascii=False, indent=2, default=str)}\n```"
        )
        return BRIEFING_SYSTEM, user

    def generate(self, view: dict[str, Any], raw: dict[str, Any]) -> str:
        if not llm.available():
            logger.warning("LLM unavailable — template briefing")
            return llm.fallback_report(view)
        system, user = self.build_prompt(view, raw)
        try:
            text = llm.chat(system, user, temperature=0.35, max_tokens=8000)
            if len(text) < 200:
                raise RuntimeError("briefing too short")
            return text
        except Exception as exc:
            logger.exception("Briefing failed: %s", exc)
            return llm.fallback_report(view, note=f"LLM error: {exc}")

    def run(self, view: dict[str, Any], raw: dict[str, Any] | None = None) -> str:
        raw = raw if raw is not None else self.storage.list_raw()
        markdown = self.generate(view, raw)
        self.storage.write_report(markdown)
        packs = self.write_article_packs(view, raw)
        logger.info("[%s] wrote %d article packs", self.name, len(packs))
        return markdown

    def write_article_packs(self, view: dict[str, Any], raw: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(self.config.get("max_article_drafts", 3))
        allowed = {
            p.get("id")
            for p in (self.config.get("pillars") or [])
            if isinstance(p, dict) and p.get("id")
        }
        ranked = view.get("ranked_candidates") or []
        if allowed:
            ranked = [c for c in ranked if (c.get("pillar") or "city") in allowed]
        candidates = _pick_interesting_mix(ranked, limit)
        packs = []
        for idx, cand in enumerate(candidates, start=1):
            if ledger.is_seen(cand, today=self.storage.as_of):
                logger.info("Skip already covered: %s", cand.get("title"))
                continue
            try:
                packs.append(self._one_pack(idx, cand, view))
            except Exception as exc:
                logger.exception("Draft pack failed for %s: %s", cand.get("title"), exc)
        return packs

    def _one_pack(
        self,
        idx: int,
        cand: dict[str, Any],
        view: dict[str, Any],
        *,
        force: bool = False,
        keep_hero: bool = False,
        existing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not force and ledger.is_seen(cand, today=self.storage.as_of):
            raise RuntimeError(f"already covered: {cand.get('title')}")
        slug = (existing or {}).get("slug") or _slug(self.storage.as_of, idx, cand)
        sources = _source_bundle(cand)
        body = self._draft_article(cand, view, sources)
        body = _ensure_source_footer(body, sources)
        old_hero = (existing or {}).get("hero") or {}
        if keep_hero and old_hero.get("ok") and old_hero.get("path") and Path(old_hero["path"]).exists():
            hero = old_hero
        else:
            hero = self._maybe_hero(slug, cand, body)
        rel_image = None
        if hero.get("ok") and hero.get("path"):
            rel_image = f"images/{Path(hero['path']).name}"
        if rel_image and "![hero]" not in body and "![" not in body[:400]:
            credit = None
            if not hero.get("ai_generated"):
                credit = f"圖：來源附圖。{hero.get('credit') or ''}".strip()
            body = _inject_hero(body, rel_image, credit=credit)
        md_path = self.storage.write_draft_md(slug, body)
        meta = {
            "slug": slug,
            "status": "draft_pending_review",
            "as_of": self.storage.as_of,
            "pillar": cand.get("pillar"),
            "format": cand.get("format"),
            "district": cand.get("district"),
            "headline": _first_heading(body) or cand.get("title"),
            "title_source": cand.get("title"),
            "sources": sources,
            "web": {
                "excerpt": _standfirst(body),
                "og_title": _first_heading(body) or cand.get("title"),
                "og_description": _standfirst(body),
            },
            "facebook": {
                "caption": _facebook_caption(body, cand),
                "visual_thesis": _standfirst(body),
            },
            "hero": hero,
            "needs_visual": None if hero.get("ok") else {
                "kind": "illustration_or_map",
                "proves": cand.get("title"),
            },
            "disclaimer_required": True,
            "article_path": str(md_path),
        }
        self.storage.write_draft_json(slug, meta)
        ledger.mark(cand, slug=slug, status="drafted", as_of=self.storage.as_of)
        return meta

    def _draft_article(self, cand: dict[str, Any], view: dict[str, Any], sources: list[dict[str, Any]]) -> str:
        model = "template"
        if llm.available():
            try:
                model = get_llm_config().get("model", "deepseek")
                hook = cand.get("hook") or cand.get("title")
                dek = cand.get("dek") or ""
                slim = {
                    "hook": hook,
                    "dek": dek,
                    "title": cand.get("title"),
                    "pillar": cand.get("pillar"),
                    "format": cand.get("format"),
                    "district": cand.get("district"),
                    "tier": cand.get("tier"),
                    "link": cand.get("link"),
                    "summary": (cand.get("summary") or "")[:800],
                }
                user = (
                    f"寫一篇可以刊登的香港口語繁體雜誌特稿。正文必須 {MIN_ARTICLE_CJK}–{MAX_ARTICLE_CJK} 字"
                    "（只計中文字，唔計標點同來源）。少過 700 字當未寫完。\n"
                    f"第一行必須係標題：# {hook}\n"
                    f"第二段用一句 dek（唔好印「Standfirst」呢個字）：{dek}\n"
                    "來源 summary 裡每個數字、日期、人名、地名都要用。唔好因為材料短就寫兩段交差。\n"
                    "只寫下列來源裡有的事。不要虛構。不要解釋你的寫作決定。\n"
                    f"候選：{json.dumps(slim, ensure_ascii=False)}\n"
                    f"來源：{json.dumps(sources, ensure_ascii=False)}\n"
                    f"文末必須加上：{DISCLAIMER}\n"
                )
                body = llm.chat(ARTICLE_SYSTEM, user, temperature=0.55, max_tokens=8000)
                n = _cjk_len(body)
                if n < MIN_ARTICLE_CJK or _looks_like_worksheet(body):
                    body = llm.chat(
                        ARTICLE_SYSTEM,
                        user + f"\n上一稿得 {n} 字。重寫成雜誌特稿，必須寫滿 {MIN_ARTICLE_CJK} 字。"
                        "小標題要為此篇新造。來源裡的數字全部寫入正文。\n",
                        temperature=0.6,
                        max_tokens=8000,
                    )
                    n = _cjk_len(body)
                    if n < MIN_ARTICLE_CJK or _looks_like_worksheet(body):
                        body = llm.chat(
                            ARTICLE_SYSTEM,
                            user + f"\n上一稿仍然得 {n} 字。再寫一次，正文必須 {MIN_ARTICLE_CJK}–{MAX_ARTICLE_CJK} 字。"
                            "把來源 summary 拆開寫：人、地、數、決定各寫一段。唔好發明。\n",
                            temperature=0.65,
                            max_tokens=8000,
                        )
                        n = _cjk_len(body)
                        if n < MIN_ARTICLE_CJK or n > MAX_ARTICLE_CJK + 80 or _looks_like_worksheet(body):
                            raise RuntimeError(f"article still short or worksheet ({n} 字)")
                return f"<!-- model: {model} -->\n\n{body.strip()}\n"
            except Exception as exc:
                logger.exception("Article LLM failed: %s", exc)
                raise
        raise RuntimeError("LLM unavailable — will not save a stub")

    def _maybe_hero(self, slug: str, cand: dict[str, Any], body: str) -> dict[str, Any]:
        if self.config.get("skip_images"):
            return {"ok": False, "reason": "skip_images"}
        dest = self.storage.draft_image_path(slug, ".jpg")
        urls = []
        for src in cand.get("sources") or []:
            link = src.get("link") or src.get("url")
            if link:
                urls.append(link)
        if cand.get("link"):
            urls.insert(0, cand["link"])
        press = images.fetch_press_image(urls, dest)
        if press and press.get("ok"):
            return press
        if not images.available():
            return {"ok": False, "reason": "no press image and KIE_API_KEY missing"}
        prompt = (
            f"Hong Kong city-change magazine hero. Topic: {cand.get('hook') or cand.get('title')}. "
            f"District: {cand.get('district') or 'Hong Kong'}. "
            f"Pillar: {cand.get('pillar')}. "
            "Forward-looking conceptual map / diagram. Constructive, innovative energy, not grim. "
            "No photoreal street photo. "
            f"Thesis: {cand.get('dek') or _standfirst(body) or cand.get('title')}"
        )
        try:
            return images.generate_illustration(prompt, dest.with_suffix(".png"))
        except Exception as exc:
            logger.warning("Hero image failed: %s", exc)
            return {"ok": False, "reason": str(exc)}


def _briefing_context(view: dict[str, Any]) -> dict[str, Any]:
    return {
        "as_of": view.get("as_of"),
        "independent_summary": view.get("independent_summary"),
        "property_snapshot": view.get("property_snapshot"),
        "pillar_mix": view.get("pillar_mix"),
        "candidates": [
            {
                "title": c.get("title"),
                "pillar": c.get("pillar"),
                "district": c.get("district"),
                "tier": c.get("tier"),
                "recommendation": c.get("recommendation"),
                "score": c.get("score"),
                "link": c.get("link"),
            }
            for c in (view.get("ranked_candidates") or [])[:12]
        ],
    }


def _source_bundle(cand: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    seen: set[str] = set()
    pool = list(cand.get("sources") or [])
    if not pool:
        pool = [cand]
    for src in pool:
        link = src.get("link") or src.get("url") or ""
        if not link or link in seen:
            continue
        seen.add(link)
        rows.append(
            {
                "title": src.get("title"),
                "url": link,
                "source": src.get("source"),
                "tier": src.get("tier"),
                "published": src.get("published"),
                "summary": (src.get("summary") or "")[:800],
            }
        )
    return rows


def _packable(cand: dict[str, Any]) -> bool:
    if cand.get("recommendation") == "discard":
        return False
    if cand.get("gov_pr_echo"):
        return False
    if int(cand.get("interest") or 0) < 3:
        return False
    if cand.get("recommendation") == "publish":
        return True
    tier = int(cand.get("tier") or 5)
    if tier <= 2:
        return True
    return cand.get("collector") == "local_news" and tier <= 3


def _pick_interesting_mix(ranked: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    pool = [c for c in ranked if _packable(c)]
    pool.sort(key=lambda c: (int(c.get("interest") or 0), float(c.get("score") or 0)), reverse=True)
    picked: list[dict[str, Any]] = []
    pillars: set[str] = set()
    officials = 0
    for cand in pool:
        if len(picked) >= limit:
            break
        pillar = cand.get("pillar") or "city"
        if pillar in pillars and len(picked) < limit - 1:
            continue
        if cand.get("officials_talk"):
            if officials >= 1:
                continue
            officials += 1
        pillars.add(pillar)
        picked.append(cand)
    if len(picked) < limit:
        for cand in pool:
            if cand in picked:
                continue
            picked.append(cand)
            if len(picked) >= limit:
                break
    return picked


def _slug(as_of: str, idx: int, cand: dict[str, Any]) -> str:
    pillar = cand.get("pillar") or "city"
    digest = hashlib.sha1((cand.get("title") or cand.get("link") or str(idx)).encode()).hexdigest()[:6]
    return f"{as_of}-{idx:02d}-{pillar}-{digest}"


def _cjk_len(text: str) -> int:
    body = re.split(r"\n## 來源", text or "", maxsplit=1)[0]
    return len(re.findall(r"[\u4e00-\u9fff]", body))


def _first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


_WORKSHEET_HEADS = (
    "## 現場",
    "## 機會",
    "## 機制",
    "## 誰可以做",
    "## 變數",
    "## 窗口",
    "## 生活會點變",
    "## 威脅",
    "## 傳聞",
    "### 生意",
    "### 投資觀察",
    "### 建造",
    "**Standfirst",
    "（分析）",
    "（事實）",
    "（預測）",
    "（不確定）",
    "用户要求",
    "让我",
    "讓我仔細",
    "用户说",
    "陳伯",
    "陳先生",
    "陳太",
    "鐵閘",
    "星期二，早上",
    "現有材料",
    "按現有材料推想",
    "故不採用",
    "本文不寫",
    "來源撐",
    "下一步要",
)


def _looks_like_worksheet(markdown: str) -> bool:
    leaked = ("我需要寫", "不要虛構", "只寫稿", "用户想让我", "We need answer")
    if any(token in (markdown or "") for token in leaked):
        return True
    return sum(1 for token in _WORKSHEET_HEADS if token in markdown) >= 2


def _standfirst(markdown: str) -> str:
    m = re.search(r"\*\*Standfirst：\*\*\s*(.+)", markdown)
    if m:
        return m.group(1).strip()
    paras = [
        p.strip()
        for p in re.split(r"\n\s*\n", markdown)
        if p.strip()
        and not p.startswith("#")
        and not p.startswith("<!--")
        and not p.startswith("![")
        and not p.startswith("*圖")
    ]
    return (paras[0] if paras else "")[:180]


def _facebook_caption(markdown: str, cand: dict[str, Any]) -> str:
    thesis = _standfirst(markdown) or (cand.get("title") or "")
    return (
        f"{thesis}\n\n"
        "生意、投資觀察、建造，邊度有窗口？"
        "生活會點變，有咩威脅，定係仲有未證實的傳聞？"
    )


def _ensure_source_footer(body: str, sources: list[dict[str, Any]]) -> str:
    """Always end with a source list the model cannot skip."""
    text = re.sub(r"\n## 來源\n[\s\S]*$", "\n", body.rstrip())
    text = re.sub(r"\n" + re.escape(DISCLAIMER) + r"\s*$", "\n", text.rstrip())
    lines = ["## 來源", ""]
    if sources:
        for src in sources:
            name = src.get("source") or "來源"
            title = (src.get("title") or "").strip() or name
            url = src.get("url") or src.get("link") or ""
            if url:
                lines.append(f"- {name}：[{title}]({url})")
            else:
                lines.append(f"- {name}：{title}")
    else:
        lines.append("- （無可用連結）")
    lines.extend(["", DISCLAIMER, ""])
    return text.rstrip() + "\n\n" + "\n".join(lines)


def _inject_hero(body: str, rel_image: str, credit: str | None = None) -> str:
    lines = body.splitlines()
    out: list[str] = []
    injected = False
    block = [f"![hero]({rel_image})"]
    if credit:
        block.extend(["", f"*{credit}*"])
    for line in lines:
        out.append(line)
        if not injected and line.startswith("# "):
            out.append("")
            out.extend(block)
            injected = True
    if not injected:
        out = block + [""] + out
    return "\n".join(out) + ("\n" if not body.endswith("\n") else "")


def _template_article(cand: dict[str, Any], sources: list[dict[str, Any]], model: str) -> str:
    title = cand.get("title") or "待定題目"
    links = "\n".join(f"- {s.get('source')}: {s.get('url')}" for s in sources) or "- （無可用連結）"
    return (
        f"<!-- model: {model} -->\n\n"
        f"# {title}\n\n"
        f"這則消息可能打開一個生意、投資觀察或建造窗口——現有材料還不夠寫成完整特稿。\n\n"
        f"{cand.get('district') or '香港'}。來源標題：{title}。請編輯按原始文件補場面、機制與三個窗口。\n\n"
        f"## 來源\n\n{links}\n\n"
        f"{DISCLAIMER if cand.get('pillar') in {'property', 'economy'} else ''}\n"
    )
