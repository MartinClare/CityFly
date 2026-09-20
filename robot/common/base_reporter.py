"""Abstract reporter: view.json + raw context -> LLM narrative markdown."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from common.storage import TopicStorage

logger = logging.getLogger(__name__)


class BaseReporter(ABC):
    name: str = "base"

    def __init__(self, storage: TopicStorage, config: dict[str, Any]):
        self.storage = storage
        self.config = config

    @abstractmethod
    def build_prompt(self, view: dict[str, Any], raw: dict[str, Any]) -> tuple[str, str]:
        """Return (system_prompt, user_prompt)."""

    @abstractmethod
    def generate(self, view: dict[str, Any], raw: dict[str, Any]) -> str:
        """Call LLM (or template) and return markdown report."""

    def run(self, view: dict[str, Any], raw: dict[str, Any] | None = None) -> str:
        raw = raw if raw is not None else self.storage.list_raw()
        markdown = self.generate(view, raw)
        path = self.storage.write_report(markdown)
        logger.info("[%s] wrote report %s", self.name, path)
        return markdown
