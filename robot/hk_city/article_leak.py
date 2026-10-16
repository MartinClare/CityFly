"""Detect instruction / planning leaks in article drafts (EN + ZH)."""

from __future__ import annotations

import json
import re
from typing import Any

# Any single match anywhere in the draft → reject (not article copy).
_PLANNING_SUBSTRINGS: tuple[str, ...] = (
    # Chinese model meta / user echo
    "用户想要",
    "用户想让我",
    "用户想讓我",
    "用户要求",
    "用户说",
    "我需要仔细",
    "我需要仔細",
    "我需要寫",
    "我需要写",
    "让我仔细",
    "讓我仔細",
    "让我先",
    "讓我先",
    "我来分析",
    "我來分析",
    "按要求",
    "根據要求",
    "根据要求",
    # Echoed pipeline / system rules
    "只寫稿",
    "不要虛構",
    "不要虚构",
    "不要寫編輯室",
    "不要解释",
    "不要解釋",
    "按現有材料推想",
    "故不採用",
    "本文不寫",
    "來源撐得住",
    "來源撐",
    "下一步要核對",
    "下一步要核对",
    "只計中文字",
    "只计中文字",
    "唔好印「Standfirst」",
    "不要印 Standfirst",
    "**Standfirst",
    "OUTPUT FORMAT",
    "Output format",
    # English planning / scratch
    "We need write",
    "We need to write",
    "We need answer",
    "word count",
    "Word count",
    "Let me analyze",
    "I'll write a",
    "I will write",
    "The user wants",
    "Based on the requirements",
    "According to the prompt",
    "magazine article in",
    "Hong Kong Cantonese",
    "700-1000",
    "700–1000",
)

# Briefing / worksheet section labels (two hits → worksheet).
_WORKSHEET_HEADS: tuple[str, ...] = (
    "## 現場",
    "## 機會",
    "## 機制",
    "## 誰可以做",
    "## 變數",
    "## 窗口",
    "## 生活會點變",
    "## 威脅",
    "## 傳聞",
    "### 生意",
    "### 投資觀察",
    "### 建造",
    "（分析）",
    "（事實）",
    "（預測）",
    "（不確定）",
    "陳伯",
    "陳先生",
    "陳太",
    "鐵閘",
    "星期二，早上",
    "現有材料",
)

_OPENING_PLANNING_RE = re.compile(
    r"^(?:"
    r"We need\b|"
    r"The user\b|"
    r"Let me\b|"
    r"I(?:'ll| will)\b|"
    r"用户|"
    r"我需要|"
    r"讓我|"
    r"让我|"
    r"首先[,，]?"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

_SCRATCH_WORD_COUNT_RE = re.compile(
    r"(?:正文|body).{0,40}(?:\d{3,4}\s*字|700|800|900|1000)",
    re.IGNORECASE,
)


def looks_like_instruction_leak(markdown: str) -> bool:
    """True when text looks like model planning or echoed instructions, not magazine copy."""
    text = markdown or ""
    if not text.strip():
        return True
    for token in _PLANNING_SUBSTRINGS:
        if token in text:
            return True
        if token.isascii() and token.lower() in text.lower():
            return True
    head = text[:1200]
    if _OPENING_PLANNING_RE.search(head.lstrip()):
        return True
    if _SCRATCH_WORD_COUNT_RE.search(head):
        return True
    # Standfirst label dump in opening
    if re.search(r"Standfirst\s*[:：]", head, re.IGNORECASE) and not head.strip().startswith("#"):
        return True
    return False


def looks_like_worksheet(markdown: str) -> bool:
    """Worksheet / briefing scaffold or instruction leak."""
    if looks_like_instruction_leak(markdown):
        return True
    text = markdown or ""
    return sum(1 for token in _WORKSHEET_HEADS if token in text) >= 2


def parse_article_json(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not (data.get("title") or data.get("body")):
        return None
    return data


def assemble_article_markdown(title: str, dek: str, body: str) -> str:
    """Build canonical article markdown from structured fields."""
    title = (title or "").strip().lstrip("#").strip()
    dek = (dek or "").strip()
    body = (body or "").strip()
    parts: list[str] = [f"# {title}", ""]
    if dek:
        parts.extend([dek, ""])
    if body:
        parts.append(body)
        if not body.endswith("\n"):
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"
