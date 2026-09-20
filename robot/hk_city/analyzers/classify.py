"""Rule-based pillar / format / impact classification."""

from __future__ import annotations

import re
from typing import Any

from common.base_analyzer import BaseAnalyzer
from hk_city.analyzers.cluster import flatten_items
from hk_city.analyzers.source_copy import copy_stats, is_thin_copy

PILLAR_HINTS: dict[str, list[str]] = {
    "property": ["樓", "租金", "售價", "住宅", "房屋", "公屋", "居屋", "按揭", "單位", "成交", "空置", "地產", "重建項目"],
    "city": ["北部都會", "北都", "啟德", "西九", "填海", "新發展區", "規劃", "分區", "市建", "九龍東", "新市鎮"],
    "mobility": ["鐵路", "港鐵", "公路", "隧道", "橋", "機場", "港口", "巴士", "交通", "通勤", "道路", "航道", "路政", "交匯處"],
    "economy": ["經濟", "本地生產總值", "失業", "零售", "通脹", "利率", "旅遊", "貿易", "就業", "財政", "大灣區", "機遇", "產業"],
    "tech": ["人工智能", "AI", "智慧城市", "數碼", "創科", "科技園", "數碼港", "金融科技", "建造科技", "創新", "城市大腦"],
}

FORMAT_HINTS: dict[str, list[str]] = {
    "one_number": ["指數", "成交", "售價", "租金", "失業率", "人次", "百分比"],
    "map_detective": ["啟德", "元朗", "北都", "新界北", "西九", "東涌", "將軍澳", "洪水橋", "Kai Tak", "Hung Hom"],
    "tech_life": ["AI", "人工智能", "智慧", "城市大腦", "數碼", "數據", "私隱", "監控"],
    "rumor_watch": ["傳聞", "外界關注", "市場傳", "消息指", "據悉", "可能會"],
    "opportunity_window": ["招標", "合約", "機遇", "創科", "產業", "供應", "投資", "建造"],
    "engineer_explains": ["工程", "施工", "隧道", "橋樑", "軌道", "地盤"],
    "reality_vs_hype": ["必升", "複製", "起飛", "保證"],
    "behind_headline": ["方便", "承諾", "宣傳"],
}

DISTRICT_HINTS = [
    "中西區", "灣仔", "東區", "南區", "油尖旺", "深水埗", "九龍城", "黃大仙", "觀塘",
    "葵青", "荃灣", "屯門", "元朗", "北區", "大埔", "沙田", "西貢", "離島",
    "啟德", "東涌", "將軍澳", "天水圍", "粉嶺", "上水", "古洞", "洪水橋", "西九",
    "太古城", "黃竹坑", "土瓜灣", "屯門", "紅磡", "Kai Tak", "Hung Hom",
]


class ClassifyAnalyzer(BaseAnalyzer):
    name = "classify"

    def analyze(self, raw: dict[str, Any]) -> dict[str, Any]:
        items = [i for i in flatten_items(raw) if not str(i.get("id", "")).startswith("error:")]
        classified = [classify_item(item) for item in items]
        return {"count": len(classified), "items": classified}


def classify_item(item: dict[str, Any]) -> dict[str, Any]:
    text = f"{item.get('title') or ''} {item.get('summary') or ''}"
    collector = item.get("_collector") or item.get("collector") or ""
    pillar, pillar_score = _best_pillar(text, collector)
    fmt = _best_format(text, pillar)
    district = _first_district(text)
    tier = int(item.get("tier") or 5)
    impact = _impact(tier, pillar_score, district, collector)
    entertainment = (
        "medium"
        if district
        or fmt in {"one_number", "map_detective", "reality_vs_hype", "opportunity_window", "tech_life", "rumor_watch"}
        else "low"
    )
    authority = max(1, min(5, 6 - tier))
    timeliness = "current"
    if collector == "local_news":
        timeliness = "breaking"
    if collector == "property_data":
        timeliness = "current"
    rec = "discard"
    gov_pr = _is_gov_pr_echo(text)
    interest = _interest(text, district, fmt, collector)
    entertainment = "high" if interest >= 5 else entertainment
    thin = is_thin_copy(item)
    if thin or _is_off_brief(text) or _is_nav_page(text) or _is_thin_program(text):
        rec = "discard"
    elif collector == "consultancy":
        rec = "monitor"
    elif collector == "local_news" and _has_city_hook(text):
        rec = "publish"
    elif collector == "local_news" and tier >= 3:
        rec = "monitor"
    elif gov_pr:
        rec = "monitor"
    elif _is_thin_announce(text) and not district:
        rec = "monitor"
    elif tier <= 2 and (district or pillar_score >= 2 or impact != "low"):
        rec = "publish"
    elif tier <= 2:
        rec = "monitor"
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "link": item.get("link"),
        "source": item.get("source"),
        "published": item.get("published"),
        "summary": (item.get("summary") or "")[:800],
        "thin_copy": thin,
        "source_cjk": copy_stats(item)["cjk"],
        "tier": tier,
        "policy": item.get("policy"),
        "collector": collector,
        "pillar": pillar,
        "format": fmt,
        "district": district,
        "impact": impact,
        "entertainment": entertainment,
        "authority": authority,
        "timeliness": timeliness,
        "recommendation": rec,
        "gov_pr_echo": gov_pr,
        "city_hook": _has_city_hook(text),
        "interest": interest,
        "officials_talk": _is_officials_talk(text),
    }


COLLECTOR_PILLAR = {
    "mobility": "mobility",
    "living_housing": "property",
    "city_projects": "city",
    "city_macro": "economy",
    "tech_local": "tech",
    "property_data": "property",
    "consultancy": "property",
    "gov_news": "city",
    "local_news": "city",
}


def _best_pillar(text: str, collector: str = "") -> tuple[str, int]:
    scores = {k: sum(1 for h in hints if h.lower() in text.lower() or h in text) for k, hints in PILLAR_HINTS.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return COLLECTOR_PILLAR.get(collector, "city"), 0
    return best, scores[best]


def _best_format(text: str, pillar: str) -> str:
    for fmt, hints in FORMAT_HINTS.items():
        if any(h in text for h in hints):
            return fmt
    if pillar == "city":
        return "district_portrait"
    if pillar == "mobility":
        return "engineer_explains"
    if pillar == "property":
        return "one_number"
    return "hk_wants_to_know"


def _first_district(text: str) -> str | None:
    for name in DISTRICT_HINTS:
        if name in text:
            return name
    return None


def _impact(tier: int, pillar_score: int, district: str | None, collector: str) -> str:
    if collector == "property_data":
        return "high"
    if district and tier <= 2:
        return "high"
    if pillar_score >= 2 and tier <= 2:
        return "medium"
    if tier <= 2:
        return "medium"
    return "low"


def _is_thin_announce(text: str) -> bool:
    return bool(
        re.search(
            r"(委任|出席|演講|開放日|展覽開幕|祝賀|了解更多|我們的願景|關於我們|諮詢委員會)",
            text,
        )
    )


def _is_gov_pr_echo(text: str) -> bool:
    return bool(
        re.search(
            r"(招標承投|簽署.{0,20}合約|保養合約招標|新聞稿|惠民|穩步推進|施政報告提出)",
            text,
        )
    ) and not _has_city_hook(text)


def _has_city_hook(text: str) -> bool:
    return any(
        k in text
        for k in (
            "AI",
            "人工智能",
            "智慧",
            "城市大腦",
            "數據",
            "私隱",
            "傳聞",
            "樓價",
            "租金",
            "北都",
            "北部都會",
            "投資",
            "創科",
        )
    )


def _is_off_brief(text: str) -> bool:
    return bool(
        re.search(
            r"(亞運|手球|足球|排球|籃球|滑板|壘球|道指|納指|巴菲特|Labubu|Jellycat|"
            r"殺妻|爆竊|鯁喉|設靈|靈堂|持械行劫|偷現金|孕味|暗盤)",
            text,
        )
    )


def _is_nav_page(text: str) -> bool:
    return bool(re.search(r"(了解更多|我們的願景|關於我們|網站指南|私隱政策)", text))


def _is_thin_program(text: str) -> bool:
    title = text.split("\n", 1)[0]
    return bool(re.search(r"(開放數據計劃|數據跨境流動|合約員工|諮詢委員會|環保管理工作)", title)) and len(text) < 160


def _is_officials_talk(text: str) -> bool:
    return bool(re.match(r"^(李家超|陳國基|甯漢豪|蔡若蓮|丘應樺|卓永興|盧寵茂|王冬勝)[：:]", text.strip()))


def _has_concrete_number(text: str) -> bool:
    return bool(
        re.search(
            r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:%|％|億|萬|幅|份|宗|個|元|呎|厘|Billion|billion|Million|million)",
            text,
        )
    )


def _interest(text: str, district: str | None, fmt: str, collector: str) -> int:
    score = 0
    if _has_concrete_number(text):
        score += 3
    if district and re.search(r"(用地|重建|賣地|通車|擴闊|大學城|新站|填海|劏房|簡樸房)", text):
        score += 3
    if fmt in {"one_number", "map_detective", "rumor_watch"}:
        score += 2
    if len(text) >= 280:
        score += 1
    if collector == "property_data":
        score += 3
    if _is_officials_talk(text) and not (_has_concrete_number(text) and district):
        score -= 3
    if _is_thin_program(text) or _is_nav_page(text):
        score -= 5
    return score
