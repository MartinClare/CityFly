#!/usr/bin/env python3
"""Draft the thin-filter desk-2 covers (2026-09-19)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.config import load_env, load_topic_config
from common.storage import TopicStorage
from hk_city.analyzers.classify import classify_item
from hk_city.analyzers.source_copy import copy_stats
from hk_city.reporter import CityFlyReporter, _cjk_len


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
    for item in items:
        title = item.get("title") or ""
        link = (item.get("link") or "").rstrip("/")
        key = link or title
        if key in seen:
            continue
        if any(n in title for n in needles):
            seen.add(key)
            hits.append(item)
    return hits

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COVERS = [
    {
        "idx": 1,
        "hook": "洪水橋三幅校園地，19 間院校搶？",
        "dek": "陳國基話大學城唔止擴校，要帶動科技。",
        "needles": ["北都大學城不只供校舍", "大學城屬北都發展重要部分"],
    },
    {
        "idx": 2,
        "hook": "租金連升 9 個月",
        "dek": "8 月 CRI 加 1.65%，人才計劃再批 5 萬宗。",
        "needles": ["租金續升 三大人才"],
    },
    {
        "idx": 3,
        "hook": "西九野餐連架生都租到",
        "dek": "枱櫈風扇四五十元，做到 10 月 11。",
        "needles": ["西九想野餐"],
    },
    {
        "idx": 4,
        "hook": "局長唔答搬唔搬入北都",
        "dek": "甯漢豪：好多地方都支持，係咪要住勻？",
        "needles": ["官員無答會否搬入北都"],
    },
    {
        "idx": 5,
        "hook": "高鐵專列賣「留學香港」",
        "dek": "4 省 5 列，廣鐵話兩個月見 150 萬人。",
        "needles": ["高鐵專車4省宣傳"],
    },
    {
        "idx": 6,
        "hook": "1823 未投訴先用 AI 撈",
        "dek": "李家超話轉介快、辦得成，爭議副司長拍板。",
        "needles": ["指定部門牽頭處理1823"],
    },
    {
        "idx": 7,
        "hook": "一季信用卡燒 2865 億",
        "dek": "本地升 11%，海外消費反而平。",
        "needles": ["港信用卡次季交易額2865"],
    },
    {
        "idx": 8,
        "hook": "中信大家樂收檔",
        "dek": "政總立會少個就腳飯堂。",
        "needles": ["中信大家樂結業"],
    },
    {
        "idx": 9,
        "hook": "公務員請鐘數假？",
        "dek": "為生仔，明年先試。商界話唔會跟。",
        "needles": ["civil servants to get hourly"],
    },
    {
        "idx": 10,
        "hook": "外勞護老會搶工資？",
        "dek": "僱主警告窮人請唔起，未證實。",
        "needles": ["Foreign carer scheme"],
    },
    {
        "idx": 11,
        "hook": "深圳酒店可以即買即退稅",
        "dek": "稅務局話便利 APEC。",
        "needles": ["深圳推酒店離境退稅"],
    },
    {
        "idx": 12,
        "hook": "三跑之後衝低空經濟",
        "dek": "專欄話要由超級聯繫人變成聚合器。",
        "needles": ["拓展低空經濟"],
    },
    {
        "idx": 13,
        "hook": "照顧者飯堂想釣人出嚟",
        "dek": "陳國基話石排灣試過 250 人，避免悲劇。",
        "needles": ["社區照顧者飯堂"],
    },
    {
        "idx": 14,
        "hook": "新皇崗最快 10 月 12",
        "dek": "李家超話日子唔掛鈎任何活動。",
        "needles": ["新皇崗最快10"],
    },
    {
        "idx": 15,
        "hook": "半島酒店上 AI",
        "dek": "91% 業者仲要人手對報表，系統搬入本地機房。",
        "needles": ["半島酒店 AI 策略"],
    },
    {
        "idx": 16,
        "hook": "51 萬戶每月網購燒 $2,000+",
        "dek": "家電衫褲買少咗，學者話轉買內地平貨。",
        "needles": ["網購者增 51萬"],
    },
    {
        "idx": 17,
        "hook": "代理吹樓市全年升 15%",
        "dek": "傳聞嚟咋，信不信由你。",
        "needles": ["陰霾退卻 樓市全年升15%"],
    },
    {
        "idx": 18,
        "hook": "觀塘繞道 160 公里",
        "dek": "無人機加隱形戰車，軚盤改 180 度兩男被捕。",
        "needles": ["觀塘繞道反危駕"],
    },
    {
        "idx": 19,
        "hook": "深圳校服連顏色都統一",
        "dek": "彩藍藏青白色，色差有限值。",
        "needles": ["校服一體化"],
    },
    {
        "idx": 20,
        "hook": "內地賣樓要所見即所得",
        "dek": "住建部話現樓銷售成大勢。",
        "needles": ["賣現樓成大勢"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int)
    parser.add_argument("--from-idx", type=int, default=1)
    args = parser.parse_args()

    load_env()
    storage = TopicStorage("hk_city", as_of="2026-09-19")
    config = load_topic_config("hk_city")
    config["skip_images"] = False
    config["max_article_drafts"] = 20
    view_path = storage.processed_dir / "view.json"
    view = storage.read_json(view_path) if view_path.exists() else {
        "as_of": storage.as_of,
        "independent_summary": "desk 2：只寫有正文嘅來源。",
        "ranked_candidates": [],
    }
    items = _all_items(storage.list_raw())
    reporter = CityFlyReporter(storage, config)
    covers = [c for c in COVERS if c["idx"] == args.only] if args.only else [
        c for c in COVERS if c["idx"] >= args.from_idx
    ]
    ok = 0
    for spec in covers:
        hits = _find(items, spec)
        if not hits:
            print(f"MISSING {spec['idx']}: {spec['hook']}", flush=True)
            continue
        body = copy_stats(hits)
        if body["thin"]:
            print(
                f"SKIP {spec['idx']:02d}: thin  cjk={body['cjk']}  {spec['hook']}",
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
        print(
            f"drafting {spec['idx']:02d}: {spec['hook']}  "
            f"sources={len(hits)} cjk={body['cjk']}",
            flush=True,
        )
        try:
            meta = reporter._one_pack(spec["idx"], cand, view, force=True)
            n = _cjk_len(Path(meta["article_path"]).read_text(encoding="utf-8"))
            print(
                f"  wrote {meta.get('article_path')}  "
                f"hero={(meta.get('hero') or {}).get('ok')}  cjk={n}",
                flush=True,
            )
            ok += 1
        except Exception as exc:
            print(f"  FAILED {spec['idx']}: {exc}", flush=True)
    print(f"done {ok}/{len(covers)}")
    return 0 if ok == len(covers) else 1


if __name__ == "__main__":
    raise SystemExit(main())
