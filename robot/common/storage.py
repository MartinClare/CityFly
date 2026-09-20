"""Dated storage helpers for raw / processed / reports."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from common.config import data_root


def today_str(as_of: date | datetime | str | None = None) -> str:
    if as_of is None:
        return date.today().isoformat()
    if isinstance(as_of, str):
        return as_of
    if isinstance(as_of, datetime):
        return as_of.date().isoformat()
    return as_of.isoformat()


class TopicStorage:
    """File layout under topic/data/{raw,processed,reports}/YYYY-MM-DD/."""

    def __init__(self, topic: str, as_of: date | datetime | str | None = None):
        self.topic = topic
        self.as_of = today_str(as_of)
        self.root = data_root(topic)
        self.raw_dir = self.root / "raw" / self.as_of
        self.processed_dir = self.root / "processed" / self.as_of
        self.reports_dir = self.root / "reports"
        self.drafts_dir = self.root / "drafts" / self.as_of

    def ensure_dirs(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        (self.drafts_dir / "images").mkdir(parents=True, exist_ok=True)

    # ----- JSON -----

    def write_json(self, folder: Path, name: str, payload: Any) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=_json_default)
        return path

    def read_json(self, path: Path) -> Any:
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def write_raw_json(self, collector_name: str, payload: Any) -> Path:
        return self.write_json(self.raw_dir, f"{collector_name}.json", payload)

    def write_processed_json(self, name: str, payload: Any) -> Path:
        return self.write_json(self.processed_dir, name, payload)

    def raw_path(self, collector_name: str) -> Path:
        return self.raw_dir / f"{collector_name}.json"

    def load_raw(self, collector_name: str) -> Any | None:
        path = self.raw_path(collector_name)
        if not path.exists():
            return None
        return self.read_json(path)

    def list_raw(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if not self.raw_dir.exists():
            return out
        for path in sorted(self.raw_dir.glob("*.json")):
            out[path.stem] = self.read_json(path)
        return out

    # ----- CSV / DataFrame -----

    def write_raw_csv(self, collector_name: str, df: pd.DataFrame) -> Path:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        path = self.raw_dir / f"{collector_name}.csv"
        df.to_csv(path, index=True)
        return path

    def write_processed_csv(self, name: str, df: pd.DataFrame) -> Path:
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        path = self.processed_dir / name
        df.to_csv(path, index=True)
        return path

    # ----- Reports -----

    def report_path(self, suffix: str = ".md") -> Path:
        return self.reports_dir / f"{self.as_of}{suffix}"

    def write_report(self, markdown: str) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.report_path()
        path.write_text(markdown, encoding="utf-8")
        return path

    def write_draft_md(self, slug: str, markdown: str) -> Path:
        self.ensure_dirs()
        path = self.drafts_dir / f"{slug}.md"
        path.write_text(markdown, encoding="utf-8")
        return path

    def write_draft_json(self, slug: str, payload: Any) -> Path:
        return self.write_json(self.drafts_dir, f"{slug}.json", payload)

    def draft_image_path(self, slug: str, suffix: str = ".png") -> Path:
        return self.drafts_dir / "images" / f"{slug}{suffix}"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    if pd.isna(obj):
        return None
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def dedup_by_key(items: list[dict], key: str) -> list[dict]:
    """Preserve order, drop duplicates by key."""
    seen: set[Any] = set()
    out: list[dict] = []
    for item in items:
        k = item.get(key)
        if k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out
