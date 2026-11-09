"""Desk settings overlay on top of hk_city/config.yaml."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from common.config import data_root, topic_dir

SETTINGS_NAME = "desk-settings.json"
FEED_GROUPS = (
    "gov_news",
    "city_projects",
    "living_housing",
    "mobility",
    "city_macro",
    "local_news",
    "consultancy",
    "tech_local",
)
GROUP_LABELS = {
    "gov_news": "政府新聞",
    "city_projects": "城市項目",
    "living_housing": "房屋生活",
    "mobility": "基建交通",
    "city_macro": "宏觀經濟",
    "local_news": "本地新聞",
    "consultancy": "顧問／樓市",
    "tech_local": "本地科技",
}


def settings_path(topic: str = "hk_city") -> Path:
    return data_root(topic) / SETTINGS_NAME


def default_settings(base: dict[str, Any] | None = None) -> dict[str, Any]:
    base = base or {}
    pillars = {}
    for p in base.get("pillars") or []:
        pid = p.get("id") if isinstance(p, dict) else None
        if pid:
            pillars[pid] = True
    collectors: dict[str, Any] = {}
    for name in FEED_GROUPS:
        group = (base.get("collectors") or {}).get(name) or {}
        feeds_state = []
        for feed in group.get("feeds") or []:
            feeds_state.append({"url": feed.get("url") or "", "enabled": True})
        collectors[name] = {
            "enabled": True,
            "limit": int(group.get("limit") or 40),
            "feeds": feeds_state,
            "extra_feeds": [],
        }
    return {
        "news_limit": int(base.get("news_limit") or 160),
        "max_article_drafts": int(base.get("max_article_drafts") or 30),
        "ledger_lookback_days": int(base.get("ledger_lookback_days") or 45),
        "pillars": pillars,
        "collectors": collectors,
    }


def load_settings(topic: str = "hk_city") -> dict[str, Any]:
    path = settings_path(topic)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(data: dict[str, Any], topic: str = "hk_city") -> Path:
    path = settings_path(topic)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def merge_topic_config(base: dict[str, Any], overlay: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply desk-settings.json on top of config.yaml."""
    cfg = copy.deepcopy(base)
    overlay = overlay if overlay is not None else load_settings(cfg.get("topic") or "hk_city")
    if not overlay:
        return cfg

    for key in ("news_limit", "max_article_drafts", "ledger_lookback_days"):
        if key in overlay and overlay[key] is not None:
            cfg[key] = int(overlay[key])

    pillar_flags = overlay.get("pillars") or {}
    if pillar_flags and isinstance(cfg.get("pillars"), list):
        cfg["pillars"] = [
            p
            for p in cfg["pillars"]
            if isinstance(p, dict) and pillar_flags.get(p.get("id"), True)
        ]
        cfg["_pillar_enabled"] = {str(k): bool(v) for k, v in pillar_flags.items()}

    collectors_overlay = overlay.get("collectors") or {}
    collectors = cfg.setdefault("collectors", {})
    for name, state in collectors_overlay.items():
        if name not in collectors or not isinstance(state, dict):
            continue
        group = collectors[name]
        group["enabled"] = bool(state.get("enabled", True))
        if state.get("limit") is not None:
            group["limit"] = int(state["limit"])
        feed_flags = {
            (f.get("url") or ""): bool(f.get("enabled", True))
            for f in (state.get("feeds") or [])
            if isinstance(f, dict)
        }
        feeds = list(group.get("feeds") or [])
        for feed in feeds:
            url = feed.get("url") or ""
            if url in feed_flags:
                feed["enabled"] = feed_flags[url]
            else:
                feed.setdefault("enabled", True)
        for extra in state.get("extra_feeds") or []:
            if not isinstance(extra, dict) or not extra.get("url"):
                continue
            feeds.append(
                {
                    "name": extra.get("name") or "自訂來源",
                    "url": extra["url"],
                    "kind": extra.get("kind") or "rss",
                    "tier": int(extra.get("tier") or 3),
                    "policy": extra.get("policy") or "rss_only",
                    "enabled": bool(extra.get("enabled", True)),
                }
            )
        group["feeds"] = feeds
    return cfg


def load_yaml_raw(topic: str = "hk_city") -> dict[str, Any]:
    import yaml

    cfg_path = topic_dir(topic) / "config.yaml"
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config.yaml must be a mapping: {cfg_path}")
    return data


def ensure_settings(topic: str = "hk_city") -> dict[str, Any]:
    """Return merged settings dict for the UI (defaults filled)."""
    base = load_yaml_raw(topic)
    current = load_settings(topic)
    defaults = default_settings(base)
    if not current:
        save_settings(defaults, topic)
        return defaults
    # fill missing keys
    out = copy.deepcopy(defaults)
    for key in ("news_limit", "max_article_drafts", "ledger_lookback_days"):
        if key in current:
            out[key] = int(current[key])
    if isinstance(current.get("pillars"), dict):
        out["pillars"].update({k: bool(v) for k, v in current["pillars"].items()})
    for name, state in (current.get("collectors") or {}).items():
        if name not in out["collectors"] or not isinstance(state, dict):
            continue
        slot = out["collectors"][name]
        slot["enabled"] = bool(state.get("enabled", True))
        if state.get("limit") is not None:
            slot["limit"] = int(state["limit"])
        by_url = {(f.get("url") or ""): f for f in (state.get("feeds") or []) if isinstance(f, dict)}
        for feed in slot["feeds"]:
            url = feed.get("url") or ""
            if url in by_url:
                feed["enabled"] = bool(by_url[url].get("enabled", True))
        slot["extra_feeds"] = [
            e for e in (state.get("extra_feeds") or []) if isinstance(e, dict) and e.get("url")
        ]
    return out
