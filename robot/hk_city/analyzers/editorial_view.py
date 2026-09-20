"""Independent editorial ranking — not headline echo."""

from __future__ import annotations

from collections import Counter
from typing import Any

from common.base_analyzer import BaseAnalyzer
from hk_city.analyzers.classify import classify_item
from hk_city.analyzers.cluster import ClusterAnalyzer
from hk_city.analyzers.source_copy import copy_stats
from hk_city import ledger


class EditorialViewAnalyzer(BaseAnalyzer):
    name = "editorial_view"

    def analyze(self, raw: dict[str, Any]) -> dict[str, Any]:
        clustered = ClusterAnalyzer(self.storage, self.config).analyze(raw)
        ranked: list[dict[str, Any]] = []
        for cluster in clustered.get("clusters") or []:
            primary = (cluster.get("sources") or [{}])[0]
            row = classify_item(
                {
                    **primary,
                    "title": cluster.get("title") or primary.get("title"),
                    "link": cluster.get("link") or primary.get("link"),
                    "id": cluster.get("id"),
                    "summary": primary.get("summary") or "",
                    "_collector": cluster.get("collector") or primary.get("collector"),
                    "tier": cluster.get("primary_tier") or primary.get("tier") or 5,
                }
            )
            row["cluster_size"] = len(cluster.get("sources") or [])
            row["sources"] = cluster.get("sources") or []
            body = copy_stats(row["sources"] or [primary])
            row["source_cjk"] = body["cjk"]
            row["thin_copy"] = body["thin"]
            if body["thin"]:
                row["recommendation"] = "discard"
                row["discard_reason"] = "thin_copy"
            row["score"] = _score(row)
            seen = ledger.is_seen(row, today=self.storage.as_of)
            row["already_covered"] = bool(seen)
            if seen:
                row["recommendation"] = "already_used"
                row["covered_slug"] = seen.get("slug")
            if row["recommendation"] == "discard":
                continue
            if seen:
                continue
            ranked.append(row)

        ranked.sort(key=lambda r: (r.get("interest") or 0, r["score"]), reverse=True)
        ranked = _diversify(ranked)
        property_snapshot = _property_snapshot(raw)
        mix = dict(Counter(r["pillar"] for r in ranked[:12]))
        publishable = [r for r in ranked if r["recommendation"] == "publish"]
        summary = _summary(publishable, property_snapshot)
        return {
            "independent_summary": summary,
            "ranked_candidates": ranked[:25],
            "publishable_count": len(publishable),
            "property_snapshot": property_snapshot,
            "pillar_mix": mix,
        }


def _score(row: dict[str, Any]) -> float:
    score = 0.0
    score += {1: 5, 2: 3.5, 3: 1.5, 4: 0.5, 5: 0}.get(int(row.get("tier") or 5), 0)
    score += {"high": 3, "medium": 1.5, "low": 0}.get(row.get("impact"), 0)
    score += {"high": 1.5, "medium": 0.8, "low": 0}.get(row.get("entertainment"), 0)
    score += min(6, max(-4, int(row.get("interest") or 0))) * 0.7
    if row.get("district"):
        score += 1.2
    if row.get("collector") == "local_news" and row.get("city_hook"):
        score += 4.5
    elif row.get("collector") == "local_news":
        score += 0.2
    if row.get("collector") == "tech_local":
        score += 1.4
    if row.get("collector") == "consultancy":
        score -= 1.0
    if row.get("gov_pr_echo"):
        score -= 4.0
    if row.get("recommendation") == "publish":
        score += 1.5
    if row.get("format") in {"tech_life", "rumor_watch"}:
        score += 2.0
    if row.get("format") == "opportunity_window" and not row.get("gov_pr_echo"):
        score += 0.6
    blob = f"{row.get('title') or ''} {row.get('summary') or ''}"
    if any(k in blob for k in ("AI", "人工智能", "城市大腦", "創科", "智慧", "傳聞")):
        score += 1.5
    score += min(2, (row.get("cluster_size") or 1) - 1) * 0.3
    return round(score, 2)


def _diversify(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_pillars: Counter[str] = Counter()
    officials = 0
    out: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for row in rows:
        pillar = row.get("pillar") or "city"
        if seen_pillars[pillar] >= 3:
            deferred.append(row)
            continue
        if row.get("officials_talk") and officials >= 1 and int(row.get("interest") or 0) < 6:
            deferred.append(row)
            continue
        if row.get("officials_talk"):
            officials += 1
        seen_pillars[pillar] += 1
        out.append(row)
    return out + deferred


def _property_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    payload = raw.get("property_data") or {}
    latest = []
    for series in payload.get("series") or []:
        if series.get("error"):
            latest.append({"name": series.get("name"), "error": series.get("error")})
            continue
        latest.append({"name": series.get("name"), **(series.get("latest") or {}), "url": series.get("url")})
    return {"series": latest}


def _summary(publishable: list[dict[str, Any]], property_snapshot: dict[str, Any]) -> str:
    if not publishable:
        return "今日官方與本地來源未見高影響、可核對的城市變化候選。先監察，勿硬寫。"
    top = publishable[0]
    bits = [
        f"獨立判斷：優先寫「{top.get('title')}」（{top.get('pillar')} / {top.get('district') or '全市'}）。"
        f"問生活會點變、生意／投資觀察／建造窗口、威脅與未證實傳聞。"
        f"官方文件只是證據，不要寫成政策宣傳。"
    ]
    for series in (property_snapshot.get("series") or [])[:2]:
        if series.get("value") is not None:
            bits.append(
                f"{series.get('name')} 最新 {series.get('value')}（按月 {series.get('mom_pct')}%，按年 {series.get('yoy_pct')}%）。"
            )
    bits.append("本地新聞只作角度，不得成為唯一事實來源。")
    return " ".join(bits)
