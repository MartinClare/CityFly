"""Drop title-only / empty-body sources before they become topics."""

from __future__ import annotations

import re
from typing import Any

# Enough body to support a 700–1000 字 feature without inventing.
MIN_SUMMARY_CJK = 80
MIN_SUMMARY_EN_WORDS = 40


def summary_text(item: dict[str, Any] | None) -> str:
    if not item:
        return ""
    return (item.get("summary") or item.get("description") or "").strip()


def copy_stats(sources: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(sources, dict):
        pool = [sources]
    else:
        pool = list(sources or [])
    blob = "\n".join(summary_text(src) for src in pool)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", blob))
    words = len(re.findall(r"[A-Za-z]{3,}", blob))
    thin = cjk < MIN_SUMMARY_CJK and words < MIN_SUMMARY_EN_WORDS
    return {
        "cjk": cjk,
        "en_words": words,
        "thin": thin,
        "chars": len(blob),
    }


def is_thin_copy(sources: list[dict[str, Any]] | dict[str, Any] | None) -> bool:
    return bool(copy_stats(sources)["thin"])
