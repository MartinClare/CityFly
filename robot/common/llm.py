"""DeepSeek LLM client (OpenAI-compatible SDK)."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from openai import APIConnectionError, OpenAI

from common.config import get_llm_config

logger = logging.getLogger(__name__)


def get_client() -> tuple[OpenAI, dict[str, str]]:
    cfg = get_llm_config()
    extra: dict[str, Any] = {}
    if cfg.get("provider") == "openrouter":
        extra["default_headers"] = {
            "HTTP-Referer": "https://localhost/city-fly",
            "X-Title": "City Fly HK Magazine",
        }
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=120, **extra)
    return client, cfg


def chat(
    system: str,
    user: str,
    *,
    temperature: float = 0.4,
    max_tokens: int = 4096,
) -> str:
    client, cfg = get_client()
    model = cfg["model"]
    logger.info("Calling LLM model=%s", model)
    extra_body: dict[str, Any] = {}
    if cfg.get("provider") == "openrouter":
        extra_body["provider"] = {
            "allow_fallbacks": True,
            "data_collection": "allow",
        }

    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                extra_body=extra_body or None,
            )
            last_err = None
            break
        except APIConnectionError as exc:
            last_err = exc
            logger.warning("LLM connection failed (attempt %d/3): %s", attempt, exc)
            time.sleep(8 * attempt)
    if last_err is not None:
        raise last_err
    message = resp.choices[0].message
    content = (message.content or "").strip()
    if not content:
        reasoning = str(getattr(message, "reasoning", "") or "").strip()
        pulled = _article_from_reasoning(reasoning)
        if pulled:
            logger.info("Using article text found in model reasoning (%d chars)", len(pulled))
            content = pulled
        elif reasoning:
            logger.warning("LLM returned reasoning only; ignoring scratch notes")
    if not content:
        logger.warning("LLM returned empty content model=%s finish=%s", model, resp.choices[0].finish_reason)
    return content


def _article_from_reasoning(reasoning: str) -> str:
    if not reasoning:
        return ""
    text = reasoning.strip()
    if text.startswith("# ") or text.startswith("<!--"):
        return text
    m = re.search(r"(?:^|\n)(# .+(?:\n.+)*)", text)
    if m and len(re.findall(r"[\u4e00-\u9fff]", m.group(1))) >= 400:
        return m.group(1).strip()
    if len(re.findall(r"[\u4e00-\u9fff]", text)) >= 500:
        return text
    return ""


def available() -> bool:
    try:
        get_llm_config()
        return True
    except RuntimeError:
        return False


def fallback_report(view: dict[str, Any], note: str = "") -> str:
    lines = [
        "# 城市變化日報（模板 — LLM 未能生成）",
        "",
        f"> {note or 'Set OPENROUTER_API_KEY in .env to enable narrative generation.'}",
        "",
        "## Independent View",
        "",
        "```json",
        _safe_json(view),
        "```",
        "",
    ]
    return "\n".join(lines)


def _safe_json(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
