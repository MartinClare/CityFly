#!/usr/bin/env python3
"""Balanced 20: 10 Building.hk construction + 10 living/money/border."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.config import load_env, load_topic_config
from common.storage import TopicStorage
from hk_city.analyzers.classify import classify_item
from hk_city.analyzers.source_copy import copy_stats
from hk_city.reporter import CityFlyReporter, _cjk_len, _slug

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COVERS = [
    {"idx": 1, "hook": "紅磡重建 69 億搞掂", "dek": "中海投到市建項目，地價即時見真章。", "needles": ["China Overseas Wins HK$6.9 Billion Hung Hom"]},
    {"idx": 2, "hook": "沙嶺燒 281 億起超級電腦中心", "dek": "新界北動工，AI 基建埋位。", "needles": ["HK$28.1 Billion Supercomputing Oasis"]},
    {"idx": 3, "hook": "洪水橋五幅物流地叫緊人", "dek": "政府公開邀意向，睇邊個識玩。", "needles": ["HSK Logistics Cluster"]},
    {"idx": 4, "hook": "啟德綠色交通未通車先截標", "dek": "智慧系統截標，條軌仲未有影。", "needles": ["Kai Tak Smart & Green Transit"]},
    {"idx": 5, "hook": "邵氏舊地翻生", "dek": "清水灣動土，影城變新盤前奏。", "needles": ["Clearwater Bay Former Shaw Studios"]},
    {"idx": 6, "hook": "四大發展商夾埋食錦上路", "dek": "第二期上蓋到手，組團先有得玩。", "needles": ["Four Major Developers Form Consortium"]},
    {"idx": 7, "hook": "學生宿舍變下一舊肥肉？", "dek": "市場開始當專用宿舍係新投資，未證實會爆。", "needles": ["PBSA Become Hong Kong", "First Movers in Hong Kong's PBSA", "Hotel-to-PBSA"]},
    {"idx": 8, "hook": "今期賣地得何文田一單", "dek": "但供應報 10,190 伙，數夠唔夠你話。", "needles": ["One Ho Man Tin Site"]},
    {"idx": 9, "hook": "古洞北政府大樓埋班", "dek": "兩座綜合大樓入實施階段。", "needles": ["Kwu Tung North Twin Government"]},
    {"idx": 10, "hook": "港鐵畫南港島線西段", "dek": "規劃啟動，南區等咗好耐嗰條。", "needles": ["South Island Line (West)"]},
    {"idx": 11, "hook": "租金連升 9 個月", "dek": "8 月 CRI 加 1.65%，人才計劃再批 5 萬宗。", "needles": ["租金續升 三大人才"]},
    {"idx": 12, "hook": "洪水橋三幅校園地，19 間院校搶？", "dek": "陳國基話大學城唔止擴校，要帶動科技。", "needles": ["北都大學城不只供校舍", "大學城屬北都發展重要部分"]},
    {"idx": 13, "hook": "西九野餐連架生都租到", "dek": "枱櫈風扇四五十元，做到 10 月 11。", "needles": ["西九想野餐"]},
    {"idx": 14, "hook": "1823 未投訴先用 AI 撈", "dek": "李家超話轉介快、辦得成，爭議副司長拍板。", "needles": ["指定部門牽頭處理1823"]},
    {"idx": 15, "hook": "新皇崗最快 10 月 12", "dek": "李家超話日子唔掛鈎任何活動。", "needles": ["新皇崗最快10"]},
    {"idx": 16, "hook": "51 萬戶每月網購燒 $2,000+", "dek": "家電衫褲買少咗，學者話轉買內地平貨。", "needles": ["網購者增 51萬"]},
    {"idx": 17, "hook": "一季信用卡燒 2865 億", "dek": "本地升 11%，海外消費反而平。", "needles": ["港信用卡次季交易額2865"]},
    {"idx": 18, "hook": "局長唔答搬唔搬入北都", "dek": "甯漢豪：好多地方都支持，係咪要住勻？", "needles": ["官員無答會否搬入北都"]},
    {"idx": 19, "hook": "半島酒店上 AI", "dek": "91% 業者仲要人手對報表。", "needles": ["半島酒店 AI 策略"]},
    {"idx": 20, "hook": "代理吹樓市全年升 15%", "dek": "傳聞嚟咋，信不信由你。", "needles": ["陰霾退卻 樓市全年升15%"]},
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
    for item in items:
        title = item.get("title") or ""
        link = (item.get("link") or "").rstrip("/")
        key = link or title
        if key in seen:
            continue
        if any(n in title for n in spec["needles"]):
            seen.add(key)
            hits.append(item)
    return hits


def _existing_by_hook(storage: TopicStorage, hook: str) -> dict | None:
    for path in sorted(storage.drafts_dir.glob("*.json"), reverse=True):
        try:
            meta = storage.read_json(path)
        except Exception:
            continue
        if (meta.get("headline") or meta.get("title_source") or "") == hook:
            hero = meta.get("hero") or {}
            if hero.get("ok") and hero.get("path") and Path(hero["path"]).exists():
                return meta
    return None


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--from-idx", type=int, default=1)
    parser.add_argument("--only", type=int, default=0, help="Draft a single cover index")
    args = parser.parse_args()

    load_env()
    storage = TopicStorage("hk_city", as_of="2026-09-19")
    config = load_topic_config("hk_city")
    config["skip_images"] = False
    view_path = storage.processed_dir / "view.json"
    view = storage.read_json(view_path) if view_path.exists() else {
        "as_of": storage.as_of,
        "independent_summary": "建造同生活各半。",
        "ranked_candidates": [],
    }
    items = _all_items(storage.list_raw())
    reporter = CityFlyReporter(storage, config)
    ok = 0
    for spec in COVERS:
        if args.only and spec["idx"] != args.only:
            continue
        if spec["idx"] < args.from_idx:
            continue
        hits = _find(items, spec)
        st = copy_stats(hits)
        if not hits:
            print(f"MISSING {spec['idx']}: {spec['hook']}", flush=True)
            continue
        if st["thin"]:
            print(f"SKIP {spec['idx']:02d}: thin cjk={st['cjk']} en={st['en_words']} {spec['hook']}", flush=True)
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
        print(f"drafting {spec['idx']:02d}: {spec['hook']}  hits={len(hits)} cjk={st['cjk']} en={st['en_words']}", flush=True)
        try:
            existing = _existing_by_hook(storage, spec["hook"])
            if existing:
                existing = dict(existing)
                existing["slug"] = _slug(storage.as_of, spec["idx"], cand)
            meta = reporter._one_pack(
                spec["idx"],
                cand,
                view,
                force=True,
                keep_hero=True,
                existing=existing,
            )
            n = _cjk_len(Path(meta["article_path"]).read_text(encoding="utf-8"))
            print(f"  wrote {meta.get('article_path')}  hero={(meta.get('hero') or {}).get('ok')}  cjk={n}", flush=True)
            ok += 1
        except Exception as exc:
            print(f"  FAILED {spec['idx']}: {exc}", flush=True)
    print(f"done {ok}/{len(COVERS)}")
    return 0 if ok == len(COVERS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
