"""Growth formats: 城市實用 / 熱話解讀 / 入門熱門 — seeds, prompts, mix helpers."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from common.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

GROWTH_FORMATS = frozenset({"city_howto", "hot_explainer", "popular_entry"})

# Soft daily FB target across slots: ~2–3 growth posts/day
FB_GROWTH_BOOST = {
    "city_howto": 12,
    "hot_explainer": 14,
    "popular_entry": 16,
}

MIN_CJK = {
    "city_howto": 700,
    "hot_explainer": 700,
    "popular_entry": 550,
}
MAX_CJK = {
    "city_howto": 1000,
    "hot_explainer": 1000,
    "popular_entry": 800,
}

# Evergreen cards ship with code (synced). Draft cadence state stays under data/.
SEEDS_PATH = PROJECT_ROOT / "hk_city" / "howto_seeds.json"
SEED_STATE_PATH = PROJECT_ROOT / "hk_city" / "data" / "howto_seed_state.json"
INFOGRAPHIC_CREDIT = "圖：編輯部示意資訊圖，非實景。"

GROWTH_SYSTEM = """你是 City Sight（City Fly）的雜誌撰稿。聲線接近 Bloomberg CityLab / The Atlantic：冷靜、具體。
全文必須用繁體書面中文（雜誌散文），不是粵語口語書寫。
題材偏消費產品與商業熱話（手機、車、旅遊、運動裝備、訂閱），寫買／等／換／取消的決策，不是政府公文解讀。
標題必須像教學／攻略／對照文，不要寫成突發新聞或報道標題。
優先用：一文看清、……攻略、……怎麼選、……對照、……入門、先搞懂這幾點；可帶品牌／產品名。
禁止新聞腔標題：……突然、……再破、……曝光、……惹議、……恒指／官員／宣布式開頭。
只寫稿。不要印編輯室標籤。不要虛構價格、班次、規格、選單路徑。
來源沒有的細節略過。不要叫人必買或必賣；可寫「若此，可先核對官網當日價錢」。
不要推薦碼、不要付費排名口吻。文末 ## 來源 + 指定免責聲明。
"""

_SPINES = {
    "city_howto": (
        "這是「城市實用」howto（消費／設定／行程決策）。\n"
        "標題範式（擇一變奏，必須任務型攻略口吻）："
        "「……攻略」「一文看清：……怎麼做」「……五步設定」「……怎麼選／怎麼換」。"
        "有品牌或產品名更好。不要寫成新聞快訊標題。\n"
        "結構：攻略標題 → 一句何時適用 → "
        "3–5 個步驟或對照 → 收束（價錢／規格若在變動才加「若此，下一步可能是…」，標明可能／未證實）。\n"
        "不要發明價格、班次、開關路徑；來源沒寫就定性描述或以官網／App 當前頁面為準。\n"
    ),
    "hot_explainer": (
        "這是「熱話解讀」（最好扣住正在流傳的產品／降價／缺貨／加價）。\n"
        "標題範式：「一文看清：……到底怎麼回事」「……降價／缺貨，先搞懂這幾點」"
        "「……對照：清貨還是換代」。不要「……突然宣布／再破紀錄」新聞腔。\n"
        "結構：開頭約 80 字直接回答「這是什麼／關我荷包什麼事」→ 發生了什麼（有來源）→ "
        "為何影響生活／錢 → 下一步盯什麼（標明可能／未證實）。\n"
        "多來源時對照至少兩家；單來源也可以，不要硬湊。\n"
    ),
    "popular_entry": (
        "這是「入門熱門」：給平常不太追新聞的人。零行話假設。\n"
        "標題範式：「……入門：普通人只看這三項」「一文看清……是什麼」"
        "「不玩參數的……選購指南」。要有人人聽過的品牌／產品；不要報道式標題。\n"
        "結構：熟悉物件開場 → 一句白話定義 → 三個「你能用／可先不理」→ "
        "一個具體下一步（官網規格頁或設定）。\n"
        "不要獵奇、不要恐嚇、不要震驚體、不要必買口吻。專有名詞第一次出現要順口解釋。\n"
    ),
}


def is_growth_format(fmt: str | None) -> bool:
    return (fmt or "") in GROWTH_FORMATS


def growth_spine(fmt: str) -> str:
    return _SPINES.get(fmt, "")


def load_seeds() -> list[dict[str, Any]]:
    if not SEEDS_PATH.is_file():
        return []
    try:
        data = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("seeds") if isinstance(data, dict) else data
    return [r for r in (rows or []) if isinstance(r, dict) and r.get("id")]


def _fetch_page_summary(url: str, *, limit: int = 800) -> str:
    try:
        resp = requests.get(
            url,
            timeout=25,
            headers={"User-Agent": "CitySightRobot/1.0 (+https://www.citysight.net)"},
        )
        if resp.status_code >= 400:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
        return text[:limit]
    except Exception as exc:
        logger.info("Seed fetch failed %s: %s", url, exc)
        return ""


def materialize_seed(seed: dict[str, Any]) -> dict[str, Any] | None:
    """Build a draft candidate from a seed; skip if sources cannot be fetched."""
    urls = [u for u in (seed.get("source_urls") or []) if isinstance(u, str) and u.startswith("http")]
    if not urls:
        return None
    sources: list[dict[str, Any]] = []
    for url in urls[:4]:
        summary = _fetch_page_summary(url)
        if len(summary) < 80:
            continue
        sources.append(
            {
                "title": seed.get("hook_hint") or seed.get("topic") or url,
                "link": url,
                "url": url,
                "source": seed.get("source_labels", {}).get(url) or seed.get("source_label") or "官方頁面",
                "summary": summary,
            }
        )
    if not sources:
        logger.info("Skip seed %s — no usable fetches", seed.get("id"))
        return None
    fmt = seed.get("format") or "city_howto"
    if fmt not in GROWTH_FORMATS:
        fmt = "city_howto"
    return {
        "title": seed.get("hook_hint") or seed.get("topic"),
        "hook": seed.get("hook_hint") or seed.get("topic"),
        "dek": seed.get("dek") or "",
        "pillar": seed.get("pillar") or "city",
        "format": fmt,
        "interest": int(seed.get("interest") or 7),
        "entertainment": "high" if fmt == "popular_entry" else "medium",
        "recommendation": "publish",
        "tier": 2,
        "score": float(seed.get("score") or 5.5),
        "link": sources[0]["link"],
        "source": sources[0]["source"],
        "summary": sources[0]["summary"][:800],
        "sources": sources,
        "synthesis": "multi_source" if len(sources) >= 2 else "single_authority",
        "cluster_size": len(sources),
        "growth_seed_id": seed.get("id"),
        "infographic_prompt": seed.get("infographic_prompt") or "",
    }


def _load_seed_state() -> dict[str, str]:
    if not SEED_STATE_PATH.is_file():
        return {}
    try:
        data = json.loads(SEED_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = data.get("last_drafted") if isinstance(data, dict) else None
    if not isinstance(rows, dict):
        return {}
    return {str(k): str(v)[:10] for k, v in rows.items() if k and v}


def seeds_due_today(*, as_of: str, already: set[str]) -> list[dict[str, Any]]:
    """Pick up to one seed per growth format not used recently."""
    out: list[dict[str, Any]] = []
    used_fmt: set[str] = set()
    state = _load_seed_state()
    try:
        today = datetime.strptime(as_of, "%Y-%m-%d").date()
    except ValueError:
        today = datetime.utcnow().date()
    for seed in load_seeds():
        fmt = seed.get("format") or "city_howto"
        if fmt in used_fmt or fmt not in GROWTH_FORMATS:
            continue
        sid = str(seed.get("id") or "")
        if sid in already:
            continue
        refresh = int(seed.get("refresh_days") or 14)
        last = (state.get(sid) or seed.get("last_drafted") or "")[:10]
        if last:
            try:
                if (today - datetime.strptime(last, "%Y-%m-%d").date()) < timedelta(days=refresh):
                    continue
            except ValueError:
                pass
        cand = materialize_seed(seed)
        if not cand:
            continue
        out.append(cand)
        used_fmt.add(fmt)
        if len(out) >= 3:
            break
    return out


def mark_seed_drafted(seed_id: str, as_of: str) -> None:
    if not seed_id:
        return
    state = _load_seed_state()
    state[seed_id] = as_of[:10]
    SEED_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_drafted": state}
    SEED_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def infographic_prompt_for(cand: dict[str, Any], body: str = "") -> str:
    custom = (cand.get("infographic_prompt") or "").strip()
    topic = cand.get("hook") or cand.get("title") or "city guide"
    fmt = cand.get("format") or "city_howto"
    if custom:
        return f"Topic: {topic}. {custom}"
    if fmt == "city_howto":
        kind = "INFOGRAPHIC comparison or step chart with short Traditional Chinese labels."
    elif fmt == "hot_explainer":
        kind = "INFOGRAPHIC explainer diagram with short Traditional Chinese labels."
    else:
        kind = "INFOGRAPHIC door-opener diagram with short Traditional Chinese labels, simple icons."
    return (
        f"Topic: {topic}. {kind} Wide 16:9, muted magazine print palette, clean flat design. "
        "Short Chinese labels OK. Not a photograph. No watermarks. No bank or brand logos."
    )
