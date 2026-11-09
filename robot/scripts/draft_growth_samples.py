#!/usr/bin/env python3
"""Draft 3 diversified growth samples with kie.ai infographics."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import images, llm
from common.config import load_env, load_topic_config
from common.storage import TopicStorage
from hk_city.desk.drafts_store import DRAFTS
from hk_city.reporter import (
    CityFlyReporter,
    _cjk_len,
    _first_heading,
    _inject_hero,
)

AI_CREDIT = "圖：編輯部示意資訊圖，非實景。"


def _strip_hero(raw: str) -> str:
    lines: list[str] = []
    skip = False
    for line in raw.splitlines():
        if line.startswith("![hero]"):
            skip = True
            continue
        if skip:
            if line.startswith("*") and ("圖" in line or "示意" in line or "來源" in line):
                continue
            if not line.strip():
                skip = False
                continue
            skip = False
        lines.append(line)
    body = "\n".join(lines)
    return body + ("\n" if not body.endswith("\n") else "")


SAMPLES = [
    {
        "idx": 94,
        "format": "city_howto",
        "pillar": "mobility",
        "title": "去深圳坐公共交通：羅湖／落馬洲／西九怎麼選",
        "hook": "去深圳坐公共交通：羅湖／落馬洲／西九怎麼選",
        "dek": "三個口岸各走一條鐵路邏輯；選邊個要看出發地、行李與是否趕高鐵。",
        "instruction": (
            "這是城市實用 howto（香港出行）。書面中文。"
            "結構：何時適用→三個口岸對照（接駁鐵路、適合誰、週末要注意什麼）→收束。"
            "不要虛構具體班次與票價數字；若來源無精確鐘點，用定性描述。"
            "口岸開放安排以入境處／港鐵公布為準並在文中註明。"
        ),
        "infographic": (
            "INFOGRAPHIC comparison chart, wide 16:9. Three clear columns labelled in Traditional Chinese: "
            "羅湖, 落馬洲, 西九龍. Simple icons for train, luggage, clock. Arrows showing rail links. "
            "Muted magazine print palette, clean flat design. Short Chinese labels OK. "
            "Not a photograph. Not a real map screenshot. No watermarks."
        ),
        "sources": [
            {
                "title": "入境事務處 — 管制站資料",
                "link": "https://www.immd.gov.hk/hkt/contact_us/control_points.html",
                "source": "入境事務處",
                "summary": (
                    "Hong Kong Immigration lists control points including Lo Wu, Lok Ma Chau Spur Line, "
                    "and Hong Kong West Kowloon Station for cross-boundary rail. Opening hours and "
                    "arrangements are published by IMMD and may change; travellers should check official notices."
                ),
            },
            {
                "title": "港鐵 — 系統圖／過境行程",
                "link": "https://www.mtr.com.hk/ch/customer/services/system_map.html",
                "source": "港鐵",
                "summary": (
                    "MTR East Rail serves Lo Wu and Lok Ma Chau for Shenzhen connections; high-speed rail "
                    "uses West Kowloon. Choice depends on origin in Hong Kong, destination, and whether "
                    "connecting to mainland high-speed rail."
                ),
            },
        ],
    },
    {
        "idx": 95,
        "format": "popular_entry",
        "pillar": "city",
        "title": "北部都會區到底是什麼？一句話先搞懂",
        "hook": "北部都會區到底是什麼？一句話先搞懂",
        "dek": "政府把新界北定位為下一個大型城市發展區：住屋、產業與過境連接一起規劃。",
        "instruction": (
            "這是入門熱門：讀者平常不太追新聞。書面中文，零行話。"
            "結構：熟悉問題開場→一句白話定義→三個「跟你有關／可先不理」→一個下一步。"
            "不要虛構公頃／人口數字除非來源有。"
        ),
        "infographic": (
            "INFOGRAPHIC explainer, wide 16:9. Simple diagram of Northern Metropolis idea: "
            "three icon blocks with Traditional Chinese labels 住屋, 產業, 過境. "
            "Clean flat magazine infographic, muted harbour dusk palette. "
            "Short Chinese labels OK. Not a photograph. Not an official planning map. No watermarks."
        ),
        "sources": [
            {
                "title": "北部都會區 — 政府介紹",
                "link": "https://www.nm.gov.hk/tc/",
                "source": "北部都會區",
                "summary": (
                    "The Northern Metropolis is a Hong Kong Government strategic plan for New Territories North, "
                    "aiming to expand housing, create industry and innovation space, and improve connections "
                    "with Shenzhen."
                ),
            },
            {
                "title": "發展局",
                "link": "https://www.devb.gov.hk/tc/",
                "source": "發展局",
                "summary": (
                    "Development Bureau materials frame Northern Metropolis as integrating new development areas, "
                    "transport, and economic uses. Individual NDAs proceed through separate studies; treat the "
                    "Metropolis as a strategic umbrella, not a single finished town."
                ),
            },
        ],
    },
    {
        "idx": 96,
        "format": "hot_explainer",
        "pillar": "property",
        "title": "銀主盤拍賣為何突然變多？普通人要先搞懂什麼",
        "hook": "銀主盤拍賣為何突然變多？普通人要先搞懂什麼",
        "dek": "銀主盤是銀行收回抵押物後推拍的單位；新聞增多反映個別業主斷供壓力，不等於全市場同一節奏。",
        "instruction": (
            "這是熱話解讀（樓市）。開頭80字回答銀主盤是什麼、新聞變多不代表什麼。"
            "區分已證實（個別拍賣個案）與分析（市場壓力訊號）。"
            "不要叫人買入或避開；不要虛構成交價以外的數字。"
        ),
        "infographic": (
            "INFOGRAPHIC flow chart, wide 16:9. Traditional Chinese labels: "
            "斷供, 銀行收回, 拍賣盤, 市場訊號. Four simple steps with icons. "
            "Calm educational tone, muted print palette. Short Chinese labels OK. "
            "Not a photograph. No bank logos. No watermarks."
        ),
        "sources": [
            {
                "title": "銀主盤拍賣報道（星島等）",
                "link": "https://www.stheadline.com/",
                "source": "星島頭條",
                "summary": (
                    "Local property coverage reports mortgagee (bank repossessed) flats listed for auction, "
                    "sometimes at discounts to bank valuations. These are case-level auction listings, "
                    "not a single official citywide index."
                ),
            },
            {
                "title": "土地註冊處",
                "link": "https://www.landreg.gov.hk/",
                "source": "土地註冊處",
                "summary": (
                    "Land Registry records ownership and related instruments. Mortgagee sales appear when "
                    "lenders enforce security after default. Media upticks in auction listings can signal "
                    "stress for some mortgagors but are not a government price pronouncement."
                ),
            },
        ],
    },
]


def main() -> int:
    load_env()
    if not images.available():
        raise SystemExit("KIE_API_KEY missing")
    if not llm.available():
        raise SystemExit("LLM unavailable")

    day = datetime.now(ZoneInfo("Asia/Hong_Kong")).date().isoformat()
    storage = TopicStorage("hk_city", as_of=day)
    config = load_topic_config("hk_city")
    config["skip_images"] = True
    view: dict = {}
    vp = storage.processed_dir / "view.json"
    if vp.exists():
        view = json.loads(vp.read_text(encoding="utf-8"))

    reporter = CityFlyReporter(storage, config)
    results = []

    for spec in SAMPLES:
        fmt = spec["format"]
        pillar = spec["pillar"]
        print("===", fmt, pillar, flush=True)
        cand = {
            "title": spec["title"],
            "hook": spec["hook"],
            "dek": spec["dek"],
            "pillar": pillar,
            "format": fmt,
            "future_life": False,
            "interest": 8,
            "entertainment": "high" if fmt != "city_howto" else "medium",
            "recommendation": "publish",
            "tier": 2,
            "score": 6.5,
            "link": spec["sources"][0]["link"],
            "source": spec["sources"][0]["source"],
            "summary": spec["sources"][0]["summary"] + "\n\n【寫作指示】" + spec["instruction"],
            "sources": spec["sources"],
            "synthesis": "multi_source",
            "cluster_size": 2,
        }
        # Reuse existing draft body if idx already drafted (e.g. 94)
        existing_slug = None
        for p in (DRAFTS / day).glob(f"{day}-{spec['idx']:02d}-*.md"):
            existing_slug = p.stem
            break

        if existing_slug:
            slug = existing_slug
            meta = json.loads((DRAFTS / day / f"{slug}.json").read_text(encoding="utf-8"))
            print(" reuse draft", slug, flush=True)
        else:
            meta = reporter._one_pack(spec["idx"], cand, view, force=True)
            slug = meta["slug"]
            print(" drafted", slug, flush=True)

        dest = DRAFTS / day / "images" / f"{slug}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        topic = spec["hook"]
        extra = spec["infographic"]
        prompt = "Topic: " + topic + ". " + extra
        print(" kie infographic…", flush=True)
        hero = images.generate_illustration(prompt, dest)
        print(" image ok", dest.exists(), dest.stat().st_size if dest.exists() else 0, flush=True)

        md_path = DRAFTS / day / f"{slug}.md"
        body = _inject_hero(_strip_hero(md_path.read_text(encoding="utf-8")), f"images/{dest.name}", credit=AI_CREDIT)
        md_path.write_text(body, encoding="utf-8")

        meta["format"] = fmt
        meta["growth_sample"] = True
        meta["status"] = "draft_pending_review"
        meta["headline"] = _first_heading(body) or meta.get("headline")
        meta["hero"] = dict(hero)
        meta["hero"]["visual_kind"] = "infographic"
        meta["needs_visual"] = None
        fb = dict(meta.get("facebook") or {})
        fb["visual_thesis"] = "資訊圖：" + topic
        meta["facebook"] = fb
        (DRAFTS / day / f"{slug}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        row = {
            "format": fmt,
            "pillar": pillar,
            "slug": slug,
            "headline": meta["headline"],
            "cjk": _cjk_len(body),
            "infographic": str(dest),
            "desk": f"https://desk.citysight.net/a/{day}/{slug}",
        }
        results.append(row)
        print(" done", row["headline"], flush=True)

    print("===SUMMARY===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
