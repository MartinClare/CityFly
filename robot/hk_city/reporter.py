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

ARTICLE_SYSTEM = """你是 City Sight（City Fly）的雜誌撰稿。聲線接近 Bloomberg CityLab / The Atlantic：冷靜、具體。
全文必須用繁體書面中文（雜誌散文），不是粵語口語書寫（避免以唔會／嚟／嘅／啲作預設語氣）。
英文只保留專有名詞與讀者慣用的詞，例如 AI、WeChat、CCL、OpenAI。
香港可以是場景或證據，但要把利害寫給更廣的中文讀者（生活、工作、出行、資產、城市建設）。

只寫稿。不要寫編輯室、研究過程、或你為什麼這樣寫。
不要印出「現場／機會／機制／Standfirst／（預測）」等編輯室標籤。

不准：
- 發明人名、對話、街道場面、星期二早上
- 發明數字、日期、未見於來源的傳聞
- 在正文解釋「來源沒有」「現有材料看不到」「本文不寫」「故不採用」「按現有材料推想」「來源撐得住」「這是宣稱不是結論」「下一步要核對的文件」
- 讚政策；叫人買、賣、租、入市
- 把任何一家媒體的標題當自己的標題；不要用「據 XX 報道」串起全文

來源沒有的細節，略過。不要向讀者交代你略過了什麼。
官員怎麼說，就寫他怎麼說。讀者自己判斷。

結構（寫進敘事，不要印標籤）：
1. 第一行：# 自寫的書面中文 hook 標題（反差／數字／張力）
2. 第二段：一句書面中文 dek（誰／何處／什麼數字）——回答標題張力的事實線
3. 開頭 80–120 字：用來源裡的人、地、數或決定製造問題感
4. 中段推進：多來源時至少織入兩家事實或數字對照；寫清什麼在變、利害何在
5. 收束：回答開頭問題；標明已證實／分析／可能／未證實傳聞；一句「若此，下一步可能是…」條件展望（日期、機制、誰受影響、什麼會推翻傳聞），勿虛構
6. 正文 700–1000 字（只計中文字）。最多 3 個為此篇新造的小標題
7. 文末 ## 來源 + 指定免責聲明
"""

ADVANCED_TECH_ARTICLE_SYSTEM = """你是 City Sight（City Fly）的雜誌撰稿。聲線接近 Bloomberg CityLab / The Atlantic：冷靜、具體。
全文必須用繁體書面中文（雜誌散文），不是粵語口語書寫。英文只保留專有名詞與讀者慣用的詞，例如 AI、OpenAI、Tesla、CUDA。
把技術寫成會怎樣改變普通人未來幾年的生活、工作、出行、電力、醫療、私隱或常用裝置——讀者不限於香港口語圈。

來源標題是英文雜誌原題，只作事實來源，不可把英文原題當作中文標題貼上。

只寫稿。不要寫編輯室、研究過程、或你為什麼這樣寫。
不要印出「現場／機會／機制／Standfirst／（預測）」等編輯室標籤。

不准：
- 發明人名、對話、街道場面、星期二早上
- 發明數字、日期、未見於來源的傳聞
- 在正文解釋「來源沒有」「現有材料看不到」「本文不寫」「故不採用」「按現有材料推想」「來源撐得住」「這是宣稱不是結論」「下一步要核對的文件」
- 讚政策；叫人買、賣、租、入市
- 用「據 XX 報道」串起全文

來源沒有的細節，略過。不要向讀者交代你略過了什麼。

結構（寫進敘事，不要印標籤）：
1. 第一行：# 自寫的書面中文標題（面向生活會怎樣變，不要翻譯腔）
2. 第二段：一句書面中文 dek，不要印 Standfirst
3. 開頭製造問題感；多來源時織入至少兩家事實
4. 收束含條件展望「若此，下一步可能是…」（標明可能／未證實）；勿虛構
5. 正文 700–1000 字（只計中文字）。少過 700 字就未完。最多 3 個為此篇新造的小標題
6. 文末 ## 來源 + 指定免責聲明
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
            text = llm.chat(system, user, temperature=0.35, max_tokens=16000)
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
        from hk_city.auto_approve import export_site, review_day

        review_day(self.storage.as_of)
        export_site()
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
        already_today = _drafts_today(self.storage.as_of)
        packs = []
        for idx, cand in enumerate(candidates, start=1):
            if ledger.is_seen(cand, today=self.storage.as_of) or _same_story_today(cand, already_today):
                logger.info("Skip already covered: %s", cand.get("title"))
                continue
            from hk_city.analyzers.classify import off_brief_kind

            if off_brief_kind(cand.get("title") or "", cand.get("summary") or ""):
                logger.info("Skip crime, disease, or death: %s", cand.get("title"))
                continue
            from hk_city.analyzers.classify import advanced_tech_headline_drop, is_future_life_tech

            drop = advanced_tech_headline_drop(cand.get("title") or "", cand.get("summary") or "")
            if drop == "geopolitics":
                logger.info("Skip geopolitics in tech funnel: %s", cand.get("title"))
                continue
            # Tech pillar: future-life / big-brand first; gov PR allowed as lower-priority filler.
            if cand.get("pillar") == "tech" or cand.get("advanced_tech"):
                if not is_future_life_tech(cand) and not cand.get("gov_tech_pr"):
                    logger.info("Skip tech without future-life / brand / gov-pr keep: %s", cand.get("title"))
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
            "synthesis": cand.get("synthesis")
            or (
                "multi_source"
                if len(sources) >= 2
                else (
                    "single_authority"
                    if (cand.get("future_life") or cand.get("advanced_tech"))
                    else "single"
                )
            ),
            "cluster_size": int(cand.get("cluster_size") or len(sources) or 1),
            "interest": cand.get("interest"),
            "entertainment": cand.get("entertainment"),
            "future_life": cand.get("future_life"),
            "advanced_tech": cand.get("advanced_tech"),
            "gov_tech_pr": cand.get("gov_tech_pr"),
            "score": cand.get("score"),
            "disclaimer_required": True,
            "article_path": str(md_path),
        }
        self.storage.write_draft_json(slug, meta)
        ledger.mark(cand, slug=slug, status="drafted", as_of=self.storage.as_of)
        return meta

    def _draft_article(self, cand: dict[str, Any], view: dict[str, Any], sources: list[dict[str, Any]]) -> str:
        if llm.available():
            try:
                advanced = bool(cand.get("advanced_tech"))
                system = ADVANCED_TECH_ARTICLE_SYSTEM if advanced else ARTICLE_SYSTEM
                hook = cand.get("hook") or cand.get("title")
                dek = cand.get("dek") or ""
                slim = {
                    "hook": hook,
                    "dek": dek,
                    "title": cand.get("title"),
                    "title_source": cand.get("title"),
                    "pillar": cand.get("pillar"),
                    "format": cand.get("format"),
                    "district": cand.get("district"),
                    "tier": cand.get("tier"),
                    "link": cand.get("link"),
                    "summary": (cand.get("summary") or "")[:800],
                    "advanced_tech": advanced,
                    "future_life": cand.get("future_life"),
                }
                multi = len(sources) >= 2
                overseas_tech = bool(
                    advanced
                    or cand.get("future_life")
                    or cand.get("advanced_tech")
                )
                if multi:
                    weave = (
                        "這是多來源合成稿：至少織入兩家來源的事實或數字，寫成 City Sight 自己的角度，"
                        "不要複述任何一家的標題結構。各來源 angles 欄的數字／日期必須用上。\n"
                    )
                elif overseas_tech:
                    # Unwire / brand blogs / product notes rarely have HK multi-outlet clusters.
                    weave = (
                        "這是海外或單一權威來源的科技特稿：不必硬湊第二家媒體，也不要虛構第二來源。"
                        "用這一則來源的事實與 angles，寫成 City Sight 自己的生活／工作向度；"
                        "說明普通人未來幾年會怎樣受影響。\n"
                    )
                else:
                    weave = "來源 summary 與 angles 裡的數字、日期、人名、地名都要用。\n"
                spine = (
                    "結構：自寫 hook 標題 → dek → 開頭張力 → 推進 → 收束並含條件展望"
                    "「若此，下一步可能是…」（標明可能／未證實）。不要印編輯室標籤。\n"
                )
                if advanced:
                    user = (
                        f"寫一篇可以刊登的繁體書面中文雜誌特稿。正文必須 {MIN_ARTICLE_CJK}–{MAX_ARTICLE_CJK} 字"
                        "（只計中文字，不計標點與來源）。少過 700 字當未寫完。\n"
                        "第一行必須是你自寫的書面中文標題：# ……\n"
                        "不要把英文原題當標題；英文原題只在來源資料裡。\n"
                        "第二段用一句書面中文 dek（不要印「Standfirst」這個字）。\n"
                        "寫清這項技術怎樣改變普通人未來幾年的生活、工作、出行、電力、醫療、私隱或常用裝置。\n"
                        f"{weave}{spine}"
                        "只寫下列來源裡有的事。不要虛構。不要解釋你的寫作決定。\n"
                        f"候選：{json.dumps(slim, ensure_ascii=False)}\n"
                        f"來源：{json.dumps(sources, ensure_ascii=False)}\n"
                        f"文末必須加上：{DISCLAIMER}\n"
                    )
                else:
                    user = (
                        f"寫一篇可以刊登的繁體書面中文雜誌特稿。正文必須 {MIN_ARTICLE_CJK}–{MAX_ARTICLE_CJK} 字"
                        "（只計中文字，不計標點與來源）。少過 700 字當未寫完。\n"
                        "第一行必須是你自寫的書面中文 hook 標題：# ……"
                        f"（可參考角度：{hook}；不要照抄單一來源標題）\n"
                        f"第二段用一句書面中文 dek（不要印「Standfirst」）：{dek or '（自寫一句事實線）'}\n"
                        f"{weave}{spine}"
                        "只寫下列來源裡有的事。不要虛構。不要解釋你的寫作決定。\n"
                        f"候選：{json.dumps(slim, ensure_ascii=False)}\n"
                        f"來源：{json.dumps(sources, ensure_ascii=False)}\n"
                        f"文末必須加上：{DISCLAIMER}\n"
                    )
                body = llm.chat(system, user, temperature=0.55, max_tokens=16000)
                temps = (0.6, 0.65)
                for attempt in range(3):
                    reason = _article_reject_reason(body, advanced=advanced)
                    if not reason:
                        break
                    n = _cjk_len(body)
                    if attempt >= 2:
                        raise RuntimeError(f"article rejected ({reason}, {n} 字)")
                    if reason == "too_long":
                        nudge = (
                            f"\n上一稿得 {n} 字，太長。請壓縮成 {MIN_ARTICLE_CJK}–{MAX_ARTICLE_CJK} 字"
                            "雜誌特稿，保留關鍵數字與來源事實，刪去重複與推論注腳。\n"
                        )
                    elif reason == "too_short":
                        nudge = (
                            f"\n上一稿得 {n} 字。重寫成雜誌特稿，必須寫滿 {MIN_ARTICLE_CJK} 字。"
                            "小標題要為此篇新造。來源裡的數字全部寫入正文。\n"
                        )
                    elif reason == "english_title":
                        nudge = (
                            f"\n上一稿標題仍是英文或幾乎無中文（{n} 字正文）。"
                            "第一行 # 標題必須是書面中文，不可照抄英文原題。\n"
                        )
                    else:
                        nudge = (
                            f"\n上一稿不像成品（{n} 字）。再寫一次可刊登雜誌特稿，"
                            f"正文必須 {MIN_ARTICLE_CJK}–{MAX_ARTICLE_CJK} 字，不要工作紙格式。\n"
                        )
                    if advanced and reason != "english_title":
                        nudge += "標題必須是書面中文，不可保留英文原題。\n"
                    body = llm.chat(system, user + nudge, temperature=temps[attempt], max_tokens=16000)
                return f"{body.strip()}\n"
            except Exception as exc:
                logger.exception("Article LLM failed: %s", exc)
                raise
        raise RuntimeError("LLM unavailable — will not save a stub")

    def _maybe_hero(self, slug: str, cand: dict[str, Any], body: str) -> dict[str, Any]:
        if self.config.get("skip_images"):
            return {"ok": False, "reason": "skip_images"}
        dest = self.storage.draft_image_path(slug, ".jpg")
        image_url = cand.get("image_url")
        if not image_url:
            for src in cand.get("sources") or []:
                if src.get("image_url"):
                    image_url = src["image_url"]
                    break
        if image_url and not images.is_aggregator_page(image_url):
            credit = f"{cand.get('source') or ''} {cand.get('link') or ''}".strip() or None
            feed_hero = images.download_direct_image(image_url, dest, credit=credit)
            if feed_hero and feed_hero.get("ok"):
                return feed_hero
        urls = []
        for src in cand.get("sources") or []:
            link = src.get("link") or src.get("url")
            if link:
                urls.append(link)
        if cand.get("link"):
            urls.insert(0, cand["link"])
        # Never scrape Yahoo/Google News/MSN pages for heroes (related-story thumbs).
        press_urls = [u for u in urls if not images.is_aggregator_page(u)]
        press = images.fetch_press_image(press_urls, dest) if press_urls else None
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


_ANGLE_RE = re.compile(
    r"("
    r"\d{4}年\d{1,2}月\d{1,2}日|"
    r"\d{1,2}月\d{1,2}日|"
    r"20\d{2}年|"
    r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|"
    r"\d+(?:\.\d+)?%|"
    r"\d+(?:\.\d+)?\s*(?:億|萬|千|倍|宗|伙|個|人|元|港元|美元|公里|米|小時)"
    r")"
)


def _extract_angles(text: str, *, limit: int = 8) -> list[str]:
    """Pull salient numbers/dates from a source blurb for the drafting model."""
    blob = re.sub(r"\s+", " ", (text or "").strip())
    if not blob:
        return []
    hits: list[str] = []
    seen: set[str] = set()
    for m in _ANGLE_RE.finditer(blob):
        tok = m.group(0).strip()
        if not tok or tok in seen:
            continue
        seen.add(tok)
        hits.append(tok)
        if len(hits) >= limit:
            break
    return hits


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
        summary = (src.get("summary") or "")[:800]
        title = src.get("title") or ""
        row = {
            "title": title,
            "url": link,
            "source": src.get("source"),
            "tier": src.get("tier"),
            "published": src.get("published"),
            "summary": summary,
            "angles": _extract_angles(f"{title} {summary}"),
        }
        if src.get("image_url"):
            row["image_url"] = src["image_url"]
        rows.append(row)
    return rows

def _packable(cand: dict[str, Any]) -> bool:
    if cand.get("recommendation") == "discard":
        return False
    if cand.get("gov_pr_echo"):
        return False
    if int(cand.get("interest") or 0) < 3:
        return False
    if cand.get("pillar") == "tech" or cand.get("advanced_tech"):
        from hk_city.analyzers.classify import advanced_tech_headline_drop, is_future_life_tech

        if advanced_tech_headline_drop(cand.get("title") or "", cand.get("summary") or "") == "geopolitics":
            return False
        if not is_future_life_tech(cand) and not cand.get("gov_tech_pr"):
            return False
    if cand.get("recommendation") == "publish":
        return True
    tier = int(cand.get("tier") or 5)
    if tier <= 2:
        return True
    return cand.get("collector") == "local_news" and tier <= 3


def _drafts_today(day: str) -> list[dict[str, Any]]:
    from hk_city.desk.drafts_store import DRAFTS

    folder = DRAFTS / day
    if not folder.is_dir():
        return []
    rows = []
    for js in folder.glob("*.json"):
        try:
            meta = json.loads(js.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(meta, dict):
            meta.setdefault("slug", js.stem)
            rows.append(meta)
    return rows


def _same_story_today(cand: dict[str, Any], existing: list[dict[str, Any]]) -> bool:
    from hk_city.auto_approve import similar

    sources = list(cand.get("sources") or [])
    if cand.get("link") or cand.get("url"):
        sources.append({"url": cand.get("link") or cand.get("url"), "title": cand.get("title")})
    probe = {
        "headline": cand.get("hook") or cand.get("title"),
        "title_source": cand.get("title"),
        "sources": sources,
    }
    return any(similar(probe, row) for row in existing)


def _theme_tokens(cand: dict[str, Any]) -> set[str]:
    """CJK bigrams + Latin tokens for cousin matching."""
    blob = f"{cand.get('title') or ''} {cand.get('district') or ''} {cand.get('summary') or ''}"
    toks: set[str] = set()
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9+.\-]{1,}", blob):
        toks.add(m.group(0).lower())
    cjk = re.findall(r"[\u4e00-\u9fff]", blob)
    for i in range(len(cjk) - 1):
        toks.add(cjk[i] + cjk[i + 1])
    # Drop ultra-common noise bigrams
    for noise in ("香港", "今日", "表示", "報道", "新聞", "可能", "一個", "我們"):
        toks.discard(noise)
    return toks


def _cousin_pair(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """Related-but-not-duplicate: mid title similarity or shared theme tokens."""
    from difflib import SequenceMatcher

    if (a.get("pillar") or "city") != (b.get("pillar") or "city"):
        return False
    ta = ledger.title_key(a.get("title") or a.get("hook"))
    tb = ledger.title_key(b.get("title") or b.get("hook"))
    if len(ta) >= 8 and len(tb) >= 8:
        ratio = SequenceMatcher(None, ta, tb).ratio()
        if ratio >= ledger.SIMILAR:
            return False  # already same-event cluster territory
        if 0.55 <= ratio < ledger.SIMILAR:
            return True
    shared = _theme_tokens(a) & _theme_tokens(b)
    strong = {t for t in shared if len(t) >= 2 and (t.isascii() or len(t) >= 2)}
    # Need a real entity overlap (brand/district/product), not one weak bigram
    if a.get("district") and a.get("district") == b.get("district") and len(strong) >= 2:
        return True
    return len(strong) >= 3


def _merge_cousin_candidates(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse related cousins (max 3) into one pack with unioned sources."""
    pool = [dict(c) for c in ranked if _packable(c)]
    pool.sort(
        key=lambda c: (
            0 if c.get("gov_tech_pr") else 1,
            len(c.get("sources") or []),
            int(c.get("interest") or 0),
            float(c.get("score") or 0),
        ),
        reverse=True,
    )
    merged: list[dict[str, Any]] = []
    used: set[int] = set()
    for i, primary in enumerate(pool):
        if i in used:
            continue
        group = [primary]
        used.add(i)
        for j, other in enumerate(pool):
            if j in used or len(group) >= 3:
                continue
            if any(_cousin_pair(g, other) for g in group):
                group.append(other)
                used.add(j)
        if len(group) == 1:
            row = primary
            nsrc = len(row.get("sources") or []) or (1 if row.get("link") else 0)
            row.setdefault("cluster_size", max(1, nsrc))
            if nsrc >= 2 and not row.get("synthesis"):
                row["synthesis"] = "multi_source"
            merged.append(row)
            continue
        # Highest-score row stays primary; union sources
        group.sort(
            key=lambda c: (int(c.get("interest") or 0), float(c.get("score") or 0)),
            reverse=True,
        )
        head = dict(group[0])
        seen_links: set[str] = set()
        sources: list[dict[str, Any]] = []
        for g in group:
            for src in g.get("sources") or [g]:
                link = (src.get("link") or src.get("url") or "").strip()
                if link and link in seen_links:
                    continue
                if link:
                    seen_links.add(link)
                sources.append(src if isinstance(src, dict) else g)
            link = (g.get("link") or g.get("url") or "").strip()
            if link and link not in seen_links:
                seen_links.add(link)
                sources.append(
                    {
                        "title": g.get("title"),
                        "link": link,
                        "source": g.get("source"),
                        "summary": g.get("summary"),
                        "tier": g.get("tier"),
                    }
                )
        head["sources"] = sources
        head["cluster_size"] = max(len(sources), len(group))
        head["synthesis"] = "cousin_feature"
        # Prefer multi-source packs in later ranking
        head["score"] = float(head.get("score") or 0) + min(3, len(sources) - 1) * 0.8
        merged.append(head)
    return merged


def _is_overseas_tech(cand: dict[str, Any]) -> bool:
    """Future-life / advanced tech often arrives as one authoritative outlet (Unwire, brand blog)."""
    return bool(cand.get("future_life") or cand.get("advanced_tech"))


def _pick_interesting_mix(ranked: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    pool = _merge_cousin_candidates(ranked)

    def _rank_key(c: dict[str, Any]) -> tuple:
        multi = c.get("synthesis") in {"multi_source", "cousin_feature"} or len(c.get("sources") or []) >= 2
        # Local HK stories: prefer multi-source. Overseas tech: single authority is fine —
        # don't let a thin two-outlet local cluster outrank a strong Unwire/brand piece.
        multi_boost = 0 if _is_overseas_tech(c) else (1 if multi else 0)
        return (
            0 if c.get("gov_tech_pr") else 1,
            1 if _is_overseas_tech(c) else 0,
            multi_boost,
            int(c.get("interest") or 0),
            float(c.get("score") or 0),
        )

    # Future-life tech first; multi-source boost only for non-overseas; then interest.
    pool.sort(key=_rank_key, reverse=True)
    picked: list[dict[str, Any]] = []
    pillars: set[str] = set()
    officials = 0
    gov_tech = 0
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
        # Cap government tech PR so it never crowds out the edition.
        if cand.get("gov_tech_pr"):
            if gov_tech >= 1:
                continue
            gov_tech += 1
        pillars.add(pillar)
        picked.append(cand)
    if len(picked) < limit:
        for cand in pool:
            if cand in picked:
                continue
            if cand.get("gov_tech_pr") and gov_tech >= 1:
                continue
            if cand.get("gov_tech_pr"):
                gov_tech += 1
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


def _heading_still_english(markdown: str) -> bool:
    """True when the H1 has almost no CJK — overseas drafts must not keep the English title."""
    from hk_city.auto_approve import english_title

    heading = _first_heading(markdown)
    if not heading:
        return True
    if english_title(heading):
        return True
    return len(re.findall(r"[\u4e00-\u9fff]", heading)) < 4


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


def _article_reject_reason(markdown: str, *, advanced: bool = False) -> str | None:
    """None when the draft is publishable length/shape; else a short reject code."""
    n = _cjk_len(markdown)
    if n < MIN_ARTICLE_CJK:
        return "too_short"
    if n > MAX_ARTICLE_CJK + 80:
        return "too_long"
    if _looks_like_worksheet(markdown):
        return "worksheet"
    if advanced and _heading_still_english(markdown):
        return "english_title"
    return None


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
    """Standfirst + one attention-drawing question (no fixed desk slogan)."""
    from hk_city.facebook_publish import closing_question_for_draft

    thesis = _standfirst(markdown) or (cand.get("title") or "")
    meta = {
        "headline": cand.get("hook") or cand.get("title") or thesis,
        "dek": cand.get("dek") or "",
        "web": {"excerpt": thesis},
        "pillar": cand.get("pillar"),
    }
    question = closing_question_for_draft(meta)
    return f"{thesis}\n\n{question}"


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
        f"# {title}\n\n"
        f"這則消息可能打開一個生意、投資觀察或建造窗口——現有材料還不夠寫成完整特稿。\n\n"
        f"{cand.get('district') or '香港'}。來源標題：{title}。請編輯按原始文件補場面、機制與三個窗口。\n\n"
        f"## 來源\n\n{links}\n\n"
        f"{DISCLAIMER if cand.get('pillar') in {'property', 'economy'} else ''}\n"
    )
