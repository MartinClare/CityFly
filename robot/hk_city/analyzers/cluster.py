"""Dedupe near-duplicate headlines and URLs."""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

from common.base_analyzer import BaseAnalyzer
from hk_city.ledger import SIMILAR, title_key


class ClusterAnalyzer(BaseAnalyzer):
    name = "cluster"

    def analyze(self, raw: dict[str, Any]) -> dict[str, Any]:
        items = flatten_items(raw)
        clusters: list[dict[str, Any]] = []
        seen: dict[str, int] = {}
        for item in items:
            if str(item.get("id", "")).startswith("error:"):
                continue
            key = _cluster_key(item)
            if key in seen:
                clusters[seen[key]]["sources"].append(_slim(item))
                continue
            seen[key] = len(clusters)
            clusters.append(
                {
                    "id": key,
                    "title": item.get("title") or "",
                    "link": item.get("link") or "",
                    "published": item.get("published"),
                    "primary_tier": item.get("tier", 5),
                    "collector": item.get("_collector"),
                    "sources": [_slim(item)],
                }
            )
        clusters = _merge_similar_titles(clusters)
        return {"count": len(clusters), "clusters": clusters}


def _merge_similar_titles(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same event on Unwire and the outlets it cites becomes one cluster."""
    merged: list[dict[str, Any]] = []
    keys: list[str] = []
    for cluster in clusters:
        key = title_key(cluster.get("title"))
        hit = -1
        if len(key) >= 10:
            for i, other in enumerate(keys):
                if len(other) >= 10 and SequenceMatcher(None, key, other).ratio() >= SIMILAR:
                    hit = i
                    break
        if hit < 0:
            merged.append(cluster)
            keys.append(key)
            continue
        dest = merged[hit]
        seen_links = {(s.get("link") or "") for s in dest.get("sources") or []}
        for src in cluster.get("sources") or []:
            link = src.get("link") or ""
            if link and link in seen_links:
                continue
            dest.setdefault("sources", []).append(src)
            if link:
                seen_links.add(link)
        try:
            if int(cluster.get("primary_tier") or 9) < int(dest.get("primary_tier") or 9):
                dest["title"] = cluster.get("title") or dest.get("title")
                dest["link"] = cluster.get("link") or dest.get("link")
                dest["primary_tier"] = cluster.get("primary_tier")
                keys[hit] = title_key(dest.get("title"))
        except (TypeError, ValueError):
            pass
    return merged


def flatten_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for collector, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        for item in payload.get("items") or []:
            if isinstance(item, dict):
                row = dict(item)
                row["_collector"] = collector
                items.append(row)
    return items


def _slim(item: dict[str, Any]) -> dict[str, Any]:
    row = {
        "source": item.get("source"),
        "title": item.get("title"),
        "link": item.get("link"),
        "published": item.get("published"),
        "tier": item.get("tier"),
        "policy": item.get("policy"),
        "summary": (item.get("summary") or "")[:1200],
        "collector": item.get("_collector"),
    }
    if item.get("image_url"):
        row["image_url"] = item["image_url"]
    return row


def _cluster_key(item: dict[str, Any]) -> str:
    link = (item.get("link") or "").strip()
    if link:
        parsed = urlparse(link)
        path = parsed.netloc + parsed.path.rstrip("/")
        if parsed.query:
            path += "?" + parsed.query
        if path:
            return "url:" + path.lower()
    title = re.sub(r"\s+", "", (item.get("title") or "").lower())
    title = re.sub(r"[^\w\u4e00-\u9fff]", "", title)[:40]
    if title:
        return "t:" + title
    return "h:" + hashlib.sha1(str(item.get("id", "")).encode()).hexdigest()[:10]
