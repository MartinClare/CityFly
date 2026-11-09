#!/usr/bin/env python3
"""Smoke-check multi-source merge, angles, editorial boost, FB attractiveness."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hk_city.analyzers.editorial_view import _score  # noqa: E402
from hk_city.auto_approve import invented_forecast_certainty  # noqa: E402
from hk_city.facebook_publish import fb_attractiveness  # noqa: E402
from hk_city.reporter import (  # noqa: E402
    _extract_angles,
    _merge_cousin_candidates,
    _source_bundle,
)


def main() -> int:
    fails: list[str] = []

    angles = _extract_angles("路政署要求港鐵兩周內交報告，涉東涌西站 3.2億 工程於2026年11月8日發現問題。")
    if not angles:
        fails.append("angles empty")
    else:
        print("angles ok:", angles[:5])

    a = {
        "pillar": "property",
        "title": "新界北粉嶺新盤首推 呎價1.2萬",
        "summary": "粉嶺某盤首推200伙，呎價約1.2萬港元。",
        "district": "北區",
        "link": "https://example.com/a",
        "source": "明報",
        "interest": 7,
        "score": 4.0,
        "recommendation": "publish",
        "tier": 2,
        "sources": [
            {
                "title": "新界北粉嶺新盤首推 呎價1.2萬",
                "link": "https://example.com/a",
                "summary": "粉嶺某盤首推200伙，呎價約1.2萬港元。",
                "source": "明報",
            }
        ],
    }
    b = {
        "pillar": "property",
        "title": "粉嶺新盤市場反應 成交節奏加快",
        "summary": "粉嶺新盤連日成交加快，發展商或加推。",
        "district": "北區",
        "link": "https://example.com/b",
        "source": "星島",
        "interest": 6,
        "score": 3.5,
        "recommendation": "publish",
        "tier": 2,
        "sources": [
            {
                "title": "粉嶺新盤市場反應 成交節奏加快",
                "link": "https://example.com/b",
                "summary": "粉嶺新盤連日成交加快，發展商或加推。",
                "source": "星島",
            }
        ],
    }
    c = {
        "pillar": "tech",
        "title": "Google 筆電系統更新釋放 6GB 記憶體",
        "summary": "Googlebook 更新降低本地 AI 記憶體壓力。",
        "link": "https://example.com/c",
        "source": "Unwire",
        "interest": 8,
        "score": 5.0,
        "recommendation": "publish",
        "tier": 2,
        "future_life": True,
        "sources": [
            {
                "title": "Google 筆電系統更新釋放 6GB 記憶體",
                "link": "https://example.com/c",
                "summary": "Googlebook 更新降低本地 AI 記憶體壓力 6GB。",
                "source": "Unwire",
            }
        ],
    }
    merged = _merge_cousin_candidates([a, b, c])
    cousin = next((m for m in merged if m.get("synthesis") == "cousin_feature"), None)
    if not cousin:
        fails.append("cousin_feature not produced")
    else:
        nsrc = len(cousin.get("sources") or [])
        print(f"cousin ok: sources={nsrc} cluster={cousin.get('cluster_size')}")
        if nsrc < 2:
            fails.append("cousin sources < 2")
        bundle = _source_bundle(cousin)
        if not any(row.get("angles") for row in bundle):
            fails.append("source bundle missing angles")
        else:
            print("bundle angles ok:", [row.get("angles") for row in bundle])

    # Unrelated same-pillar tech must NOT cousin-merge
    unrelated = _merge_cousin_candidates(
        [
            {
                "pillar": "tech",
                "title": "ChatGPT 突现封号风波 Pro用户也遭殃",
                "summary": "OpenAI 账号异常。",
                "link": "https://example.com/chatgpt",
                "interest": 7,
                "score": 4.0,
                "recommendation": "publish",
                "tier": 2,
                "future_life": True,
                "sources": [{"title": "ChatGPT 突现封号风波", "link": "https://example.com/chatgpt", "summary": "封号", "source": "cnBeta"}],
            },
            {
                "pillar": "tech",
                "title": "华强北显卡价格一天两变 RTX 5080下跌",
                "summary": "显卡行情波动。",
                "link": "https://example.com/gpu",
                "interest": 6,
                "score": 3.0,
                "recommendation": "publish",
                "tier": 2,
                "future_life": True,
                "sources": [{"title": "华强北显卡价格", "link": "https://example.com/gpu", "summary": "跌价", "source": "cnBeta"}],
            },
            {
                "pillar": "tech",
                "title": "奔驰弃用L3自动驾驶 使用条件过于苛刻",
                "summary": "车企调整自动驾驶策略。",
                "link": "https://example.com/benz",
                "interest": 6,
                "score": 3.0,
                "recommendation": "publish",
                "tier": 2,
                "future_life": True,
                "sources": [{"title": "奔驰弃用L3", "link": "https://example.com/benz", "summary": "L3", "source": "cnBeta"}],
            },
        ]
    )
    bad = [m for m in unrelated if m.get("synthesis") == "cousin_feature"]
    if bad:
        fails.append(f"unrelated tech wrongly cousin-merged: {[m.get('title') for m in bad]}")
    else:
        print("unrelated tech not merged ok:", len(unrelated))

    thin = {"interest": 5, "cluster_size": 1, "headline": "普通消息"}
    fat = {
        "interest": 5,
        "cluster_size": 3,
        "synthesis": "multi_source",
        "headline": "呎價1.2萬：粉嶺新盤節奏一變",
        "placement": "a1",
    }
    if fb_attractiveness(fat) <= fb_attractiveness(thin):
        fails.append("fb_attract multi-source should beat thin")
    else:
        print("fb_attract ok:", fb_attractiveness(thin), "<", fb_attractiveness(fat))

    single = {"cluster_size": 1, "interest": 5, "entertainment": "low"}
    multi = {"cluster_size": 3, "interest": 5, "entertainment": "low"}
    if _score(multi) <= _score(single):
        fails.append("editorial cluster boost missing")
    else:
        print("editorial score ok:", _score(single), "<", _score(multi))

    hard = "……因此樓價必然會在下季升一成。\n\n## 來源\n- x"
    soft = "……若此，下一步可能是發展商加快加推；屬分析，未證實傳聞。\n\n## 來源\n- x"
    if not invented_forecast_certainty(hard):
        fails.append("should flag hard forecast")
    if invented_forecast_certainty(soft):
        fails.append("should allow hedged forecast")
    else:
        print("forecast gate ok")

    # Overseas tech: single Unwire-style piece must not lose mix rank to thin multi-local.
    from hk_city.reporter import _pick_interesting_mix

    unwire = {
        "pillar": "tech",
        "title": "OpenAI 新模型讓筆電端側推理更快",
        "summary": "端側推理延遲下降，普通人筆電可跑本地助理。",
        "link": "https://example.com/unwire",
        "source": "Unwire",
        "interest": 8,
        "score": 5.0,
        "recommendation": "publish",
        "tier": 2,
        "future_life": True,
        "advanced_tech": True,
        "sources": [
            {
                "title": "OpenAI 新模型讓筆電端側推理更快",
                "link": "https://example.com/unwire",
                "summary": "端側推理延遲下降。",
                "source": "Unwire",
            }
        ],
    }
    thin_multi_a = {
        "pillar": "city",
        "title": "某區行人通道改善工程招標",
        "summary": "工務部門為行人通道改善工程招標。",
        "district": "觀塘",
        "link": "https://example.com/city-a",
        "interest": 4,
        "score": 2.0,
        "recommendation": "publish",
        "tier": 2,
        "sources": [
            {"title": "某區行人通道改善工程招標", "link": "https://example.com/city-a", "summary": "招標。", "source": "政府"}
        ],
    }
    thin_multi_b = {
        "pillar": "city",
        "title": "觀塘行人通道工程稍後動工",
        "summary": "觀塘行人通道改善稍後動工。",
        "district": "觀塘",
        "link": "https://example.com/city-b",
        "interest": 4,
        "score": 2.0,
        "recommendation": "publish",
        "tier": 2,
        "sources": [
            {"title": "觀塘行人通道工程稍後動工", "link": "https://example.com/city-b", "summary": "動工。", "source": "明報"}
        ],
    }
    mix = _pick_interesting_mix([thin_multi_a, thin_multi_b, unwire], 2)
    if not mix or not mix[0].get("future_life"):
        fails.append("overseas single tech should rank above thin local multi")
    else:
        print("overseas single-tech rank ok:", mix[0].get("title")[:24])

    if fb_attractiveness({"interest": 7, "cluster_size": 1, "future_life": True, "headline": "端側 AI"}) < 40:
        fails.append("future_life single should not be FB-penalized")
    else:
        print("fb single-authority tech ok:", fb_attractiveness({"interest": 7, "cluster_size": 1, "future_life": True, "advanced_tech": True, "headline": "端側 AI 更快"}))

    from hk_city.analyzers.classify import classify_item
    from hk_city.growth_formats import is_growth_format, load_seeds
    from hk_city.reporter import _article_reject_reason, _length_bounds

    seeds = load_seeds()
    if len(seeds) < 6:
        fails.append(f"howto seeds too few: {len(seeds)}")
    else:
        print("howto seeds ok:", len(seeds))

    classified = classify_item(
        {
            "title": "旗艦突然降價 黃牛價仍高",
            "summary": "新機降價清貨，缺貨型号黃牛炒價。",
            "source": "Unwire",
        }
    )
    if classified.get("format") != "hot_explainer":
        fails.append(f"expected hot_explainer got {classified.get('format')}")
    else:
        print("classify hot_explainer ok")

    howto = {
        "pillar": "tech",
        "title": "開箱新機設定五步",
        "format": "city_howto",
        "interest": 7,
        "score": 6.0,
        "recommendation": "publish",
        "sources": [{"title": "a", "link": "https://example.com/h", "summary": "x", "source": "Apple"}],
    }
    entry = {
        "pillar": "tech",
        "title": "新 iPhone 只看三項",
        "format": "popular_entry",
        "interest": 8,
        "score": 6.4,
        "recommendation": "publish",
        "sources": [{"title": "b", "link": "https://example.com/e", "summary": "y", "source": "Apple"}],
    }
    explainer = {
        "pillar": "mobility",
        "title": "Tesla 又改價",
        "format": "hot_explainer",
        "interest": 8,
        "score": 6.5,
        "recommendation": "publish",
        "sources": [{"title": "c", "link": "https://example.com/t", "summary": "z", "source": "Tesla"}],
    }
    filler = {
        "pillar": "city",
        "title": "某區行人改善",
        "format": "district_portrait",
        "interest": 4,
        "score": 2.0,
        "recommendation": "publish",
        "sources": [{"title": "d", "link": "https://example.com/d", "summary": "w", "source": "gov"}],
    }
    growth_mix = _pick_interesting_mix([howto, entry, explainer, filler], 3)
    growth_fmts = [c.get("format") for c in growth_mix if is_growth_format(c.get("format"))]
    if len(growth_fmts) > 2:
        fails.append(f"mix growth cap broken: {growth_fmts}")
    elif len(set(growth_fmts)) != len(growth_fmts):
        fails.append(f"duplicate growth format in mix: {growth_fmts}")
    else:
        print("growth mix cap ok:", growth_fmts)

    lo, hi = _length_bounds(entry)
    if lo != 550 or hi != 800:
        fails.append(f"popular_entry bounds wrong: {lo}-{hi}")
    short = "字" * 500
    if _article_reject_reason(short, cand=entry) != "too_short":
        fails.append("entry length reject failed")
    else:
        print("entry length bounds ok")

    base = fb_attractiveness({"interest": 7, "cluster_size": 1, "headline": "普通稿"})
    boosted = fb_attractiveness(
        {"interest": 7, "cluster_size": 1, "format": "popular_entry", "headline": "入門熱門稿"}
    )
    if boosted <= base:
        fails.append("popular_entry should boost FB score")
    else:
        print("fb growth boost ok:", base, "->", boosted)

    if fails:
        print("FAIL:", "; ".join(fails))
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
