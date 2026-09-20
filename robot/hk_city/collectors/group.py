"""One collector per config group (gov_news, city_projects, ...)."""

from __future__ import annotations

from typing import Any

from common.base_collector import BaseCollector
from hk_city.collectors.feeds import fetch_feed_group


class GroupCollector(BaseCollector):
    """Reads feeds from config['collectors'][name]."""

    def __init__(self, storage: Any, config: dict[str, Any], name: str):
        super().__init__(storage, config)
        self.name = name

    def fetch(self) -> dict[str, Any]:
        group = (self.config.get("collectors") or {}).get(self.name) or {}
        if group.get("enabled") is False:
            return {
                "as_of": self.storage.as_of,
                "collector": self.name,
                "items": [],
                "skipped": "disabled",
            }
        feeds = [f for f in (group.get("feeds") or []) if f.get("enabled", True)]
        limit = int(group.get("limit") or self.config.get("news_limit", 40))
        payload = fetch_feed_group(feeds, limit)
        payload["as_of"] = self.storage.as_of
        payload["collector"] = self.name
        return payload


if __name__ == "__main__":
    import logging
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO)
    from common.config import load_topic_config
    from common.storage import TopicStorage

    name = sys.argv[1] if len(sys.argv) > 1 else "gov_news"
    topic = "hk_city"
    print(GroupCollector(TopicStorage(topic), load_topic_config(topic), name).run())
