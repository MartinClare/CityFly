"""Abstract collector: fetch remote data -> dated raw snapshot."""

from __future__ import annotations

import logging
import traceback
from abc import ABC, abstractmethod
from typing import Any

from common.storage import TopicStorage

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """One data source. Failures are isolated so other collectors still run."""

    name: str = "base"

    def __init__(self, storage: TopicStorage, config: dict[str, Any]):
        self.storage = storage
        self.config = config

    @abstractmethod
    def fetch(self) -> Any:
        """Fetch and return a JSON-serializable payload (or dict with error)."""

    def run(self) -> dict[str, Any]:
        """Fetch, persist, return status dict."""
        self.storage.ensure_dirs()
        try:
            payload = self.fetch()
            path = self.storage.write_raw_json(self.name, payload)
            logger.info("[%s] wrote %s", self.name, path)
            return {"collector": self.name, "ok": True, "path": str(path)}
        except Exception as exc:
            err = {
                "collector": self.name,
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            logger.exception("[%s] failed: %s", self.name, exc)
            try:
                self.storage.write_raw_json(self.name, {"_error": err})
            except Exception:
                pass
            return err
