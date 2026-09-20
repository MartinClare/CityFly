"""Abstract analyzer: raw snapshots -> independent quantitative view."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from common.storage import TopicStorage

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    name: str = "base"

    def __init__(self, storage: TopicStorage, config: dict[str, Any]):
        self.storage = storage
        self.config = config

    @abstractmethod
    def analyze(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Return a structured view fragment (JSON-serializable)."""

    def run(self, raw: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = raw if raw is not None else self.storage.list_raw()
        logger.info("[%s] analyzing %d raw sources", self.name, len(raw))
        return self.analyze(raw)
