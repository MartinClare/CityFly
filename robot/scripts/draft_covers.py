#!/usr/bin/env python3
"""Draft the approved 20 cover stories with GPT Image 2.5 heroes."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.config import load_env, load_topic_config
from common.storage import TopicStorage
from hk_city import ledger
from hk_city.analyzers.classify import classify_item
from hk_city.analyzers.source_copy import copy_stats
from hk_city.reporter import CityFlyReporter, _cjk_len

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COVERS = [
    {
        "idx": 1,
        "hook": "北環支線話開就開？",
        "dek": "陳美寶話隨時候命，港深西部鐵路收 80 份意向書。",
        "urls": [
            "https://news.mingpao.com/pns/%e6%b8%af%e8%81%9e/article/20260919/s00002/1789751038709/%e9%99%b3%e7%be%8e%e5%af%b6-%e5%8c",
            "https://www.hyd.gov.hk/tc/information_corner/press_releases/2025/20251031/20251031.html",
            "https://www.hyd.gov.hk/tc/information_corner/press_releases/2025/20250630/20250630.html",
        ],
        "needles": ["陳美寶：北環支線可隨時動工", "收到80份意向書", "勘查、設計及建造顧問合約"],
    },
    {
        "idx": 2,
        "hook": "紅磡重建 69 億搞掂",
        "dek": "中海投到市建項目，地價即時見真章。",
        "needles": ["China Overseas Wins HK$6.9 Billion Hung Hom URA Redevelopment"],
    },
    {
        "idx": 3,
        "hook": "太古城兩房月租 2.8 萬",
        "dek": "業主笑住數錢，回報過 10 厘。",
        "needles": ["太古城兩房租2.8萬"],
    },
    {
        "idx": 4,
        "hook": "沙嶺燒 281 億起超級電腦中心",
        "dek": "新界北動工，AI 基建埋位。",
        "needles": ["HK$28.1 Billion Supercomputing Oasis Breaks Ground at Sha Ling"],
    },
    {
        "idx": 5,
        "hook": "洪水橋五幅物流地叫緊人",
        "dek": "政府公開邀意向，睇邊個識玩。",
        "needles": ["HSK Logistics Cluster: Government Invites EOI for Five Strategic Sites"],
    },
    {
        "idx": 6,
        "hook": "啟德綠色交通未通車先截標",
        "dek": "智慧系統截標，條軌仲未有影。",
        "needles": ["Kai Tak Smart & Green Transit System Tender Closes"],
    },
    {
        "idx": 7,
        "hook": "邵氏舊地翻生",
        "dek": "清水灣動土，影城變新盤前奏。",
        "needles": ["Clearwater Bay Former Shaw Studios Breaks Ground"],
    },
    {
        "idx": 8,
        "hook": "四大發展商夾埋食錦上路",
        "dek": "第二期上蓋到手，組團先有得玩。",
        "needles": ["Four Major Developers Form Consortium to Secure Kam Sheung Road"],
    },
    {
        "idx": 9,
        "hook": "學生宿舍變下一舊肥肉？",
        "dek": "市場開始當專用宿舍係新投資，未證實會爆。",
        "needles": [
            "Can PBSA Become Hong Kong's Next Investment Hotspot?",
            "First Movers in Hong Kong's PBSA Market",
            "Hotel-to-PBSA Conversions Gain Momentum",
        ],
    },
    {
        "idx": 10,
        "hook": "今期賣地得何文田一單",
        "dek": "但供應報 10,190 伙，數夠唔夠你話。",
        "needles": ["Hong Kong Limits Direct Land Sale to One Ho Man Tin Site"],
    },
    {
        "idx": 11,
        "hook": "CCL：二手今年升 12.5%",
        "dek": "豪宅仲癲，累升 14%。",
        "needles": ["CCL豪宅價今年累升14%"],
    },
    {
        "idx": 12,
        "hook": "代理吹樓市全年升 15%",
        "dek": "傳聞嚟咋，信不信由你。",
        "needles": ["廖偉強：陰霾退卻 樓市全年升15%可期"],
    },
    {
        "idx": 13,
        "hook": "51 萬戶每月網購燒 $2,000+",
        "dek": "家電衫褲買少咗，錢去晒邊？",
        "needles": ["網購者增 51萬住戶月花逾2000元"],
    },
    {
        "idx": 14,
        "hook": "新皇崗 10 月 12 通車？",
        "dek": "官方話日子唔掛鈎任何活動。",
        "needles": ["新皇崗最快10．12開通"],
    },
    {
        "idx": 15,
        "hook": "港人暑假掃深圳景點飛",
        "dek": "攜程話門票訂單升 40%。",
        "needles": ["攜程：港人愛遊深圳"],
    },
    {
        "idx": 16,
        "hook": "中大堂課強制 WeChat 點名？",
        "dek": "網傳要開 location，未證實。",
        "needles": ["網上流傳中大課堂強制用WeChat點名"],
    },
    {
        "idx": 17,
        "hook": "AI 專員月薪 26 萬",
        "dek": "施政報告開 D4 位，2027 年中先就位。",
        "needles": ["施政報告設 AI 專員一職"],
    },
    {
        "idx": 18,
        "hook": "半島酒店上 AI",
        "dek": "系統搬入本地機房，上海大酒店帶頭試。",
        "needles": ["半島酒店 AI 策略拆解"],
    },
    {
        "idx": 19,
        "hook": "古洞北政府大樓埋班",
        "dek": "兩座綜合大樓入實施階段。",
        "needles": ["Kwu Tung North Twin Government Complexes Move into Implementation Phase"],
    },
    {
        "idx": 20,
        "hook": "港鐵畫南港島線西段",
        "dek": "規劃啟動，南區等咗好耐嗰條。",
        "needles": ["MTR Begins Planning Work for South Island Line (West)"],
    },
]


def _all_items(raw: dict) -> list[dict]:
    items: list[dict] = []
    for name, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        for item in payload.get("items") or []:
            row = dict(item)
            row["_collector"] = name
            items.append(row)
    return items


def _find(items: list[dict], spec: dict) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()
    needles = spec.get("needles") or []
    urls = {u.rstrip("/") for u in (spec.get("urls") or [])}
    for item in items:
        title = item.get("title") or ""
        link = (item.get("link") or "").rstrip("/")
        key = link or title
        if key in seen:
            continue
        if (urls and link in urls) or any(n in title for n in needles):
            seen.add(key)
            hits.append(item)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, help="Draft a single cover number 1-20")
    parser.add_argument("--from-idx", type=int, default=1)
    parser.add_argument("--ids", default="", help="Comma-separated cover numbers to (re)draft")
    parser.add_argument("--force", action="store_true", help="Redraft even if the ledger already has the story")
    parser.add_argument("--keep-hero", action="store_true", help="Reuse the existing hero image")
    args = parser.parse_args()

    load_env()
    storage = TopicStorage("hk_city", as_of="2026-09-19")
    config = load_topic_config("hk_city")
    config["skip_images"] = False
    config["max_article_drafts"] = 20
    view_path = storage.processed_dir / "view.json"
    if view_path.exists():
        view = storage.read_json(view_path)
    else:
        view = {
            "as_of": storage.as_of,
            "independent_summary": "封面20條已選定。只寫來源裡有的事，唔好複讀官員口號。",
            "ranked_candidates": [],
        }
    raw = storage.list_raw()
    items = _all_items(raw)
    reporter = CityFlyReporter(storage, config)

    ok = 0
    covers = COVERS
    if args.ids:
        want = {int(x) for x in args.ids.split(",") if x.strip()}
        covers = [c for c in COVERS if c["idx"] in want]
    elif args.only:
        covers = [c for c in COVERS if c["idx"] == args.only]
    else:
        covers = [c for c in COVERS if c["idx"] >= args.from_idx]
    for spec in covers:
        hits = _find(items, spec)
        if not hits:
            print(f"MISSING {spec['idx']}: {spec['hook']}")
            continue
        body = copy_stats(hits)
        if body["thin"] and not args.force:
            print(
                f"SKIP {spec['idx']:02d}: thin source  "
                f"cjk={body['cjk']} en_words={body['en_words']}  {spec['hook']}",
                flush=True,
            )
            continue
        primary = hits[0]
        cand = classify_item(primary)
        cand.update(
            {
                "title": spec["hook"],
                "hook": spec["hook"],
                "dek": spec["dek"],
                "link": primary.get("link"),
                "summary": primary.get("summary"),
                "source": primary.get("source"),
                "published": primary.get("published"),
                "sources": hits,
            }
        )
        if not args.force and ledger.is_seen(cand, today=storage.as_of):
            print(f"SKIP {spec['idx']:02d}: already covered  {spec['hook']}", flush=True)
            continue
        existing = None
        matches = sorted(storage.drafts_dir.glob(f"{storage.as_of}-{spec['idx']:02d}-*.json"))
        if matches:
            existing = storage.read_json(matches[0])
        print(f"drafting {spec['idx']:02d}: {spec['hook']}  sources={len(hits)}", flush=True)
        try:
            meta = reporter._one_pack(
                spec["idx"],
                cand,
                view,
                force=args.force,
                keep_hero=args.keep_hero,
                existing=existing,
            )
            hero = (meta.get("hero") or {}).get("ok")
            n = _cjk_len(Path(meta["article_path"]).read_text(encoding="utf-8"))
            print(f"  wrote {meta.get('article_path')}  hero={hero}  cjk={n}", flush=True)
            ok += 1
        except Exception as exc:
            print(f"  FAILED {spec['idx']}: {exc}", flush=True)
    print(f"done {ok}/{len(covers)}")
    return 0 if ok == len(covers) else 1


if __name__ == "__main__":
    raise SystemExit(main())
