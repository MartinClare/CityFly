"""Remember publisher domains seen in Unwire attributions.

Known RSS mappings are subscribed into desk tech_local extra feeds.
Unknown domains wait on the desk Sources page.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from common.config import data_root
from hk_city.collectors.outlet_catalog import lookup_feed
from hk_city.desk.settings_store import ensure_settings, save_settings

STORE_NAME = "discovered_outlets.json"


def store_path(topic: str = "hk_city"):
    return data_root(topic) / STORE_NAME


def load_discovered(topic: str = "hk_city") -> list[dict[str, Any]]:
    path = store_path(topic)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("outlets") if isinstance(data, dict) else None
    return [r for r in (rows or []) if isinstance(r, dict) and r.get("domain")]


def save_discovered(rows: list[dict[str, Any]], topic: str = "hk_city") -> None:
    path = store_path(topic)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"outlets": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _existing_feed_urls(topic: str = "hk_city") -> set[str]:
    from hk_city.desk.settings_store import load_yaml_raw, merge_topic_config

    cfg = merge_topic_config(load_yaml_raw(topic))
    urls: set[str] = set()
    group = (cfg.get("collectors") or {}).get("tech_local") or {}
    for feed in group.get("feeds") or []:
        if isinstance(feed, dict) and feed.get("url"):
            urls.add(str(feed["url"]).rstrip("/"))
    return urls


def _subscribe(name: str, url: str, topic: str = "hk_city") -> bool:
    """Append a feed to the permanent tech_local list. Later crawls keep fetching it."""
    url = url.strip()
    if not url or url.rstrip("/") in _existing_feed_urls(topic):
        return False
    settings = ensure_settings(topic)
    slot = settings.setdefault("collectors", {}).setdefault(
        "tech_local", {"enabled": True, "limit": 50, "feeds": [], "extra_feeds": []}
    )
    extras = list(slot.get("extra_feeds") or [])
    if any((e.get("url") or "").rstrip("/") == url.rstrip("/") for e in extras):
        return False
    extras.append(
        {
            "name": name,
            "url": url,
            "kind": "rss",
            "tier": 2,
            "policy": "rss_only",
            "enabled": True,
            "via": "unwire",
        }
    )
    slot["extra_feeds"] = extras
    # The list only grows. Raise the daily cap so newer feeds are not crowded out.
    slot["limit"] = max(int(slot.get("limit") or 50), min(200, 8 * (len(extras) + 12)))
    save_settings(settings, topic)
    return True


def discover_rss(page_url: str) -> str | None:
    """Find a site's RSS from a cited article or its homepage. Empty if none."""
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    host = _domain(page_url)
    if not host:
        return None
    candidates = []
    homepage = f"https://{host}/"
    for start in (page_url, homepage):
        if start and start not in candidates:
            candidates.append(start)
    headers = {"User-Agent": "Mozilla/5.0 CityFlyBot/0.1", "Accept-Language": "en,zh;q=0.8"}
    for start in candidates:
        try:
            resp = requests.get(start, timeout=12, headers=headers)
            resp.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(resp.text, "lxml")
        for link in soup.find_all("link", href=True):
            rel = " ".join(link.get("rel") or []).lower()
            typ = (link.get("type") or "").lower()
            if "alternate" not in rel:
                continue
            if "rss" not in typ and "atom" not in typ and "xml" not in typ:
                continue
            href = urljoin(start, link["href"].strip())
            if href.startswith("http"):
                return href
    return None


def note_attributions(
    links: list[dict[str, str]], *, sample_url: str = "", topic: str = "hk_city"
) -> dict[str, int]:
    """links: {name, url}. Subscribe known RSS; queue the rest."""
    subscribed = 0
    queued = 0
    rows = load_discovered(topic)
    by_domain = {r["domain"]: r for r in rows}
    now = datetime.now(timezone.utc).isoformat()
    seen: set[str] = set()
    for link in links:
        url = (link.get("url") or "").strip()
        name = (link.get("name") or "").strip() or url
        domain = _domain(url)
        if not domain or domain in seen or "unwire." in domain:
            continue
        seen.add(domain)
        mapped = lookup_feed(domain)
        feed_name, feed_url = mapped if mapped else (name, "")
        already = by_domain.get(domain)
        if not feed_url and not (already and (already.get("dismissed") or already.get("feed_url") or int(already.get("count") or 0) > 0)):
            feed_url = discover_rss(url) or ""
            if feed_url and already is not None:
                already["feed_url"] = feed_url
        if feed_url:
            if _subscribe(feed_name or domain, feed_url, topic):
                subscribed += 1
            continue
        row = by_domain.get(domain)
        if row is None:
            row = {
                "domain": domain,
                "name": name,
                "homepage": f"https://{domain}/",
                "sample_url": url,
                "sample_article": sample_url,
                "count": 0,
                "first_seen": now,
                "dismissed": False,
            }
            rows.append(row)
            by_domain[domain] = row
            queued += 1
        elif row.get("dismissed"):
            continue
        row["count"] = int(row.get("count") or 0) + 1
        row["last_seen"] = now
        row["name"] = name or row.get("name") or domain
        row["sample_url"] = url
        if sample_url:
            row["sample_article"] = sample_url
    save_discovered(rows, topic)
    return {"subscribed": subscribed, "queued": queued}


def pending_outlets(topic: str = "hk_city") -> list[dict[str, Any]]:
    rows = [r for r in load_discovered(topic) if not r.get("dismissed")]
    rows.sort(key=lambda r: (-int(r.get("count") or 0), r.get("domain") or ""))
    return rows


def dismiss_domain(domain: str, topic: str = "hk_city") -> None:
    rows = load_discovered(topic)
    for row in rows:
        if row.get("domain") == domain:
            row["dismissed"] = True
    save_discovered(rows, topic)
