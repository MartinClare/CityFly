"""Shared RSS / HTML / metadata fetch used by all magazine collectors."""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from common.storage import dedup_by_key

logger = logging.getLogger(__name__)

FEED_TIMEOUT_SEC = 12
MAX_WORKERS = 4
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CityFlyBot/0.1"


def fetch_feed_group(feeds: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, feed): feed for feed in feeds}
        for fut in as_completed(futures):
            feed = futures[fut]
            name = feed.get("name", feed.get("url", "feed"))
            try:
                items.extend(fut.result())
            except Exception as exc:
                logger.warning("Feed %s failed: %s", name, exc)
                items.append(_error_item(feed, exc))

    items = dedup_by_key(items, "id")
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    items = items[:limit]
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }


def _fetch_one(feed: dict[str, Any]) -> list[dict[str, Any]]:
    name = feed.get("name", feed.get("url", "feed"))
    url = feed["url"]
    kind = (feed.get("kind") or "rss").lower()
    policy = feed.get("policy", "rss_only")
    logger.info("Fetching %s (%s, %s)", name, kind, policy)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-HK,zh;q=0.9,en-HK;q=0.8,en;q=0.7",
        }
    )
    resp = session.get(url, timeout=FEED_TIMEOUT_SEC)
    resp.raise_for_status()

    if kind == "html":
        items = _parse_html_list(name, url, resp.text)
    else:
        items = _parse_rss(name, resp.content)

    for item in items:
        item["tier"] = feed.get("tier", 3)
        item["policy"] = policy
        item["collector_feed"] = name
        if policy == "metadata_only":
            item["summary"] = (item.get("summary") or "")[:180]
    _enrich_article_pages(session, items, feed)
    return items


def _enrich_article_pages(session: requests.Session, items: list[dict[str, Any]], feed: dict[str, Any]) -> None:
    """Listing/RSS often has a title only. Pull the article page for Building.hk and Unwire."""
    if feed.get("policy") != "public_page_extract_allowed":
        return
    name = feed.get("name") or ""
    if "Building.hk" in name:
        targets = [it for it in items if "view.asp" in (it.get("link") or "")][:30]
    elif "Unwire" in name:
        targets = [it for it in items if it.get("link")][:20]
    else:
        return

    def one(it: dict[str, Any]) -> None:
        try:
            resp = session.get(it["link"], timeout=FEED_TIMEOUT_SEC)
            resp.raise_for_status()
            body = _article_body(resp.text)
            if len(body) >= 200:
                it["summary"] = body[:2000]
        except Exception as exc:
            logger.warning("Enrich %s failed: %s", it.get("link"), exc)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(one, targets))


def _article_body(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for sel in (".entry-content", ".post-content", "article", "#content"):
        el = soup.select_one(sel)
        if not el:
            continue
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
        if len(text) >= 200:
            return text
    chunks = [t for t in soup.stripped_strings if len(t) >= 60]
    return re.sub(r"\s+", " ", " ".join(chunks[:12])).strip()


def _parse_rss(name: str, content: bytes) -> list[dict[str, Any]]:
    parsed = feedparser.parse(content)
    items: list[dict[str, Any]] = []
    for e in parsed.entries:
        items.append(
            {
                "id": getattr(e, "id", None) or getattr(e, "link", None) or e.get("title"),
                "source": name,
                "title": getattr(e, "title", "") or "",
                "link": getattr(e, "link", "") or "",
                "summary": _strip_html(getattr(e, "summary", "") or getattr(e, "description", "") or ""),
                "published": _entry_time(e),
            }
        )
    return items


def _parse_html_list(name: str, base: str, html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        href = a["href"]
        if not title or len(title) < 10:
            continue
        if _is_nav_link(title, href):
            continue
        link = urljoin(base, href)
        if link in seen or link.rstrip("/") == base.rstrip("/"):
            continue
        seen.add(link)
        items.append(
            {
                "id": link,
                "source": name,
                "title": title[:300],
                "link": link,
                "summary": "",
                "published": None,
            }
        )
        if len(items) >= 30:
            break
    return items


_NAV_TITLES = {
    "主頁", "首頁", "Home", "English", "繁體", "简体", "Skip to content",
    "Skip to main content", "Contact us", "Client stories", "Investor relations",
    "Read the article", "Read more", "Find out more", "Manage cookies",
    "Subscribe", "Publications", "Press Releases",
}


def _is_nav_link(title: str, href: str) -> bool:
    if href.startswith("#") or href.startswith("javascript:"):
        return True
    if title in _NAV_TITLES or title.rstrip(" >»") in _NAV_TITLES:
        return True
    if re.search(r"(login|mailto:|facebook|twitter|instagram|linkedin|cookie)", href, re.I):
        return True
    if re.search(r"(arrow_forward|open_in_new|Skip to|Read the article|Subscribe)", title, re.I):
        return True
    return False


def _entry_time(entry: Any) -> str | None:
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(raw).isoformat()
        except Exception:
            return str(raw)
    return None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:500]


def _error_item(feed: dict[str, Any], exc: Exception) -> dict[str, Any]:
    name = feed.get("name", feed.get("url", "feed"))
    return {
        "id": f"error:{name}",
        "source": name,
        "title": f"[feed error] {exc}",
        "link": feed.get("url", ""),
        "summary": "",
        "published": None,
        "tier": feed.get("tier", 3),
        "policy": feed.get("policy", "rss_only"),
    }
