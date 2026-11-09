"""Rule-based pillar / format / impact classification."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from common.base_analyzer import BaseAnalyzer
from hk_city.analyzers.cluster import flatten_items
from hk_city.analyzers.source_copy import copy_stats, is_thin_copy

logger = logging.getLogger(__name__)

# Overseas tech desks that must pass future_life_gate before drafting.
ADVANCED_TECH_SOURCES = {
    "MIT Technology Review",
    "IEEE Spectrum",
    "Ars Technica",
    "Wired Science",
    "Wired",
    "Rest of World",
    "The Verge",
    "TechCrunch",
    "Engadget",
    "Bloomberg Technology",
    "CNBC Technology",
    "The Register",
    "Financial Times Technology",
    "New York Times Technology",
    "The Guardian Technology",
    "BBC Technology",
    "OpenAI",
    "Anthropic",
    "Google AI Blog",
    "Apple Newsroom",
    "MacRumors",
    "9to5Mac",
    "Tom's Hardware",
    "PCMag",
    "The Information",
    "INSIDE",
    "GIGAZINE",
    "cnBeta",
    "Samsung Newsroom",
    "Microsoft Blog",
    "Microsoft News",
    "Windows Experience Blog",
    "Windows Central",
    "GitHub Blog",
}

_ADVANCED_DROP = re.compile(
    r"(?i)\b("
    r"deal of the day|%\s*off|coupon|giveaway|"
    r"steam\b|playstation|xbox|nintendo|esports|video\s*game|"
    r"nfl|nba|mlb|nhl|super\s*bowl|world\s*cup|premier\s*league|"
    r"rocket\s*report|blue\s*origin|spacex\s+launch|falcon\s*9|"
    r"artemis\s*(ii|iii|2|3)?\b|lunar\s+mission|moon\s+landing|"
    r"the\s+download\b|weekly\s+roundup|morning\s+report|"
    r"maga\b|midterms?|democrat|republican|gop\b|"
    r"jim\s+cramer|stock\s+sell[- ]?off|don'?t\s+chase|"
    r"hands[- ]on\s+review|\breview:\s*|laptop\s+review|phone\s+review"
    r")\b"
)
# Politics / war / diplomacy — never draft these as technology.
_GEOPOLITICS = re.compile(
    r"(?i)("
    r"\b("
    r"netanyahu|hegseth|putin|zelensky|zelenskyy|hamas|hezbollah|"
    r"gaza\b|west\s+bank|ukraine\s+war|nato\b|idf\b|"
    r"white\s+house|us\s+congress|midterms?|democrat|republican|gop\b|maga\b|"
    r"presidential\s+election|election\s+campaign|denuclearization|"
    r"summit\s+with\s+(xi|putin)|iran\s+strike|missile\s+strike|"
    r"ceasefire|hostage\s+deal|foreign\s+minister|secretary\s+of\s+state"
    r")\b|"
    r"以巴|哈馬斯|普京|澤連斯基|白宮|中期選舉|共和黨|民主黨|以軍|加沙|"
    r"停火協議|外交部長|國務卿|北約|烏克蘭戰爭"
    r")"
)
_ADVANCED_KEEP_HINT = re.compile(
    r"(?i)\b("
    r"AI|model|malware|privacy|implant|organ|battery|charging|"
    r"self[- ]driving|autonomous|powertrain|grid|nuclear|smartphone|"
    r"camera|drone|medical|pharma|drug|vaccine|treatment|chip|"
    r"open[- ]weight|LLM|electric\s+vehicle|\bEV\b|charger|"
    r"data\s*cent(?:er|re)|cyberattack|ransomware|edge\s+AI"
    r")\b"
)
# Local Unwire-style life hooks (not government institution PR).
_LOCAL_TECH_LIFE = re.compile(
    r"(私隱|隱私|監控|電力|電費|電網|通勤|出行|醫療|診症|工作方式|打工|"
    r"智慧城市|城市大腦|邊緣\s*AI|Edge\s*AI|數據中心|資安|勒索軟件|"
    r"自動駕駛|電動車|充電|電池壽命|遙距工作|居家辦公|"
    r"privacy|surveillance|grid|data\s*cent|ransomware|self[- ]driving|"
    r"electric\s+vehicle|remote\s+work|smart\s+city)",
    re.I,
)
# Local tech PR we want: big consumer brands people actually buy in HK.
_BIG_BRAND_TECH = re.compile(
    r"(?i)("
    r"\bApple\b|iPhone|iPad|MacBook|AirPods|Vision\s*Pro|蘋果|"
    r"Xiaomi|小米|Redmi|紅米|"
    r"Huawei|華為|HarmonyOS|鴻蒙|"
    r"Samsung|三星|Galaxy|"
    r"\bGoogle\b|Pixel|"
    r"OPPO|vivo|一加|OnePlus|realme|榮耀|\bHonor\b|"
    r"Sony|索尼|Lenovo|聯想|ASUS|華碩|Acer|宏碁|"
    r"\bDJI\b|大疆|Tesla|特斯拉|Nvidia|英偉達|"
    r"Microsoft|微軟|Surface|\bMeta\b|OpenAI|Anthropic|"
    r"ByteDance|字節跳動|\bTikTok\b|抖音|Tencent|騰訊|Alibaba|阿里|"
    r"BYD|比亞迪|\bNothing\b|Garmin|GoPro|Belkin|Anker|羅技|\bLogitech\b"
    r")"
)
# Government / quasi-gov tech desks — crawl OK, do not draft as local tech PR.
_GOV_TECH_SOURCES = frozenset(
    {
        "數字政策辦公室",
        "數碼港新聞",
        "科學園新聞",
        "生產力促進局傳媒",
        "建造業議會新聞",
        "政府新聞公報",
    }
)
_GOV_TECH_PR = re.compile(
    r"(數字政策辦公室|數碼港|科學園|生產力促進局|建造業議會|創新科技署|"
    r"Cyberport|Science\s*Park|HKSTP|Digital\s*Policy\s*Office|"
    r"gov\.hk|諮詢委員會|開放日|施政報告|"
    r"簽署.{0,12}(備忘錄|MOU)|委任|局長|司長)",
    re.I,
)

_LIFE_SYSTEM = (
    "You judge overseas tech stories for a Hong Kong city-change magazine. "
    "Reply with one JSON line only: {\"life\": true|false, \"reason\": \"一句中文\"}. "
    "life is true when the story changes ordinary life in the next few years: "
    "work, pay, getting around, home power, medical care, privacy, or a phone, "
    "computer, or model people already use. New car technology counts "
    "(battery, charging, self-driving, powertrain, safety). Data centers that "
    "reshape electricity bills or grids count. Cyberattacks that take down "
    "everyday services count. "
    "life is false for geopolitics, war, elections, diplomacy, stock-tip "
    "columns, show-car stunts, luxury cars with no new system, product "
    "reviews, digests, rockets/space spectacle, US party politics, culture essays, "
    "or clever science with no tool people will use. "
    "reason must name the life change (or why not) in one short Chinese clause."
)

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
    source = (item.get("source") or item.get("collector_feed") or "").strip()
    advanced = is_advanced_tech_source(source)
    pillar, pillar_score = _best_pillar(text, collector)
    fmt = _best_format(text, pillar)
    if advanced:
        pillar = "tech"
        fmt = "tech_life"
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
    future_life: bool | None = None
    discard_reason: str | None = None
    gov_tech = False
    off = off_brief_kind(item.get("title") or "", item.get("summary") or "")
    if off:
        rec = "discard"
        discard_reason = off
    elif advanced:
        drop = advanced_tech_headline_drop(item.get("title") or "", item.get("summary") or "")
        if drop:
            rec = "discard"
            discard_reason = drop
            future_life = False
        elif thin:
            rec = "discard"
            discard_reason = "thin_copy"
            future_life = False
        else:
            future_life = future_life_gate(item.get("title") or "", item.get("summary") or "")
            if future_life:
                rec = "publish"
                interest = max(interest, 6)
                entertainment = "high"
                impact = "high" if impact == "low" else impact
            else:
                rec = "discard"
                discard_reason = "not_future_life"
    elif collector == "tech_local":
        # Local desk: big-brand / life-change first; government PR kept but lower priority.
        drop = advanced_tech_headline_drop(item.get("title") or "", item.get("summary") or "")
        if drop:
            rec = "discard"
            discard_reason = drop
            future_life = False
        elif _big_brand_local_tech(text, district):
            future_life = True
            rec = "publish"
            interest = max(interest, 4)
            fmt = "tech_life"
            pillar = "tech"
        elif _LOCAL_TECH_LIFE.search(text) and not _GOV_TECH_PR.search(text):
            # Non-brand Unwire life story (privacy, grid, commute) — keep.
            future_life = True
            rec = "publish"
            interest = max(interest, 4)
            fmt = "tech_life"
            pillar = "tech"
        elif _is_gov_tech_pr(source, text):
            # Keep gov / park PR, but below brands and future-life tech.
            gov_tech = True
            future_life = False
            rec = "publish"
            interest = 3  # packable floor; editorial score still ranks below brands
            fmt = "tech_life"
            pillar = "tech"
        elif thin or _is_nav_page(text) or _is_thin_program(text):
            rec = "discard"
            discard_reason = "thin_copy" if thin else "nav_or_program"
            future_life = False
        elif gov_pr or (_is_thin_announce(text) and not district):
            rec = "monitor"
            future_life = False
            discard_reason = "local_tech_pr"
        else:
            rec = "monitor"
            future_life = False
            discard_reason = "local_tech_not_life"
    elif thin or _is_nav_page(text) or _is_thin_program(text):
        rec = "discard"
        discard_reason = "thin_copy" if thin else "nav_or_program"
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
    out = {
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
        "advanced_tech": advanced,
        "future_life": future_life,
        "gov_tech_pr": gov_tech,
    }
    if item.get("image_url"):
        out["image_url"] = item["image_url"]
    if discard_reason:
        out["discard_reason"] = discard_reason
    return out


def is_advanced_tech_source(source: str) -> bool:
    name = (source or "").strip()
    if name in ADVANCED_TECH_SOURCES:
        return True
    return any(name.startswith(s) for s in ADVANCED_TECH_SOURCES)


def advanced_tech_headline_drop(headline: str, extra: str = "") -> str | None:
    """Hard drop before the life model. Cars are not dropped just for being cars."""
    blob = f"{headline or ''} {extra or ''}"
    if off_brief_kind(headline or "", extra or ""):
        return off_brief_kind(headline or "", extra or "")
    if _GEOPOLITICS.search(blob):
        return "geopolitics"
    if _ADVANCED_DROP.search(blob):
        return "advanced_drop"
    return None


def is_future_life_tech(cand: dict[str, Any]) -> bool:
    """True when a tech candidate is allowed to become a magazine draft."""
    if cand.get("future_life") is True:
        return True
    return False


def _is_gov_tech_pr(source: str, text: str) -> bool:
    """True for government / quasi-gov tech PR we should not draft as local tech."""
    name = (source or "").strip()
    if name in _GOV_TECH_SOURCES or any(name.startswith(s) for s in _GOV_TECH_SOURCES):
        return True
    # Gov-institution blurbs without a consumer brand.
    if _GOV_TECH_PR.search(text) and not _BIG_BRAND_TECH.search(text):
        return True
    return False


def _big_brand_local_tech(text: str, district: str | None) -> bool:
    """Local PR keep when a big brand product touches HK daily life."""
    if not _BIG_BRAND_TECH.search(text):
        return False
    if district:
        return True
    if re.search(r"(香港|Hong\s*Kong|\bHK\b|港人|本港|本地|發售|開賣|上市|預購)", text, re.I):
        return True
    if _LOCAL_TECH_LIFE.search(text):
        return True
    # Brand + phone/AI/car product frame is enough for Unwire-style local coverage.
    if re.search(
        r"(?i)(phone|手機|平板|筆電|耳機|手表|手錶|充電|電池|相機|筆電|"
        r"AI\b|模型|晶片|芯片|電動|自動駕駛|智能家居)",
        text,
    ):
        return True
    return False


def future_life_gate(title: str, summary: str = "") -> bool:
    """True when an overseas tech story changes future daily life."""
    from common import llm

    if not llm.available():
        return bool(_ADVANCED_KEEP_HINT.search(f"{title} {summary}"))
    user = (
        f"title: {title}\n"
        f"summary: {(summary or '')[:600]}\n"
        "Reply with one JSON line only."
    )
    try:
        text = llm.chat(_LIFE_SYSTEM, user, temperature=0, max_tokens=1024, reasoning_effort="low")
        match = re.search(r"\{.*?\}", text, re.S)
        if not match:
            return bool(_ADVANCED_KEEP_HINT.search(f"{title} {summary}"))
        data = json.loads(match.group(0))
        return bool(data.get("life"))
    except Exception as exc:
        logger.warning("future_life_gate failed for %s: %s", title, exc)
        return bool(_ADVANCED_KEEP_HINT.search(f"{title} {summary}"))


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


_DISEASE = re.compile(
    r"登革|基孔肯雅|類鼻疽|禽流感|猴痘|麻疹|霍亂|結核|日本腦炎|食物中毒|傳染病|"
    r"防護中心|確診|病徵|手足口|諾如|百日咳"
)
_DISEASE_HEAD = re.compile(r"感染|流感|疫情|病毒|新冠|武漢肺炎")
_DEATH = re.compile(
    r"離世|身亡|喪生|不治|逝世|斃命|遇難|殉職|暴斃|猝死|遇害|被殺|打死|撞死|撞斃|"
    r"墮斃|燒死人|致命|兩死|三死|墮下死亡|自殺|死亡|致死"
)
_CRIME = re.compile(
    r"謀殺案|兇殺|兇案|殺妻|搶劫|行劫|打劫|爆竊|非禮|強姦|性侵|窺淫|針孔|"
    r"毒品|吸毒|販毒|運毒|派毒|藏毒|大麻|K仔|洗黑錢|綁架|縱火|械劫|持刀|槍劫|"
    r"判囚|判監|拘捕|被捕|盜竊|入屋|罪成|罪脫|襲警|檢獲|偽造|高買|裸聊|勒索|"
    r"賣淫|貴利|臥底|偷現金|持械行劫"
)
_CRIME_HEAD = re.compile(r"詐騙|騙案|電騙")
_OTHER_OFF = re.compile(
    r"亞運|手球|足球|排球|籃球|滑板|壘球|道指|納指|巴菲特|Labubu|Jellycat|"
    r"鯁喉|設靈|靈堂|孕味|暗盤"
)


def off_brief_kind(headline: str, extra: str = "") -> str | None:
    """crime / disease / death, or other off-brief. None when the story can run.

    Arrests, case reports, and deaths match the whole blurb. Words that also
    appear in policy pieces (防騙、防自殺、疫情) only count in the headline.
    """
    head = headline or ""
    blob = f"{head} {extra or ''}"
    head = re.sub(r"防騙|反騙|投資者防騙", "", head)
    blob = re.sub(r"防騙|反騙|投資者防騙|防自殺|防止自殺|死亡交叉|交叉死亡", "", blob)
    blob = re.sub(r"(電腦|網絡|惡意).{0,6}病毒|病毒.{0,6}(電腦|網絡)", "", blob)
    if _DISEASE.search(blob) or _DISEASE_HEAD.search(head):
        return "disease"
    if _DEATH.search(blob):
        return "death"
    if _CRIME.search(blob) or _CRIME_HEAD.search(head):
        return "crime"
    if _OTHER_OFF.search(blob):
        return "off"
    return None


def _is_off_brief(text: str) -> bool:
    return off_brief_kind(text) is not None


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
