"""Configuration loading: .env, project paths, topic YAML."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")


def get_llm_config() -> dict[str, str]:
    """Resolve LLM credentials. OpenRouter is preferred when OPENROUTER_API_KEY is set."""
    load_env()
    openrouter = os.getenv("OPENROUTER_API_KEY", "").strip()
    deepseek = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if openrouter and not openrouter.startswith("sk-or-your"):
        return {
            "api_key": openrouter,
            "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek/deepseek-chat"),
            "provider": "openrouter",
        }

    if deepseek and not deepseek.startswith("sk-your-key"):
        return {
            "api_key": deepseek,
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            "provider": "deepseek",
        }

    raise RuntimeError(
        "No LLM key set. Add OPENROUTER_API_KEY (preferred) or DEEPSEEK_API_KEY to .env"
    )


def get_kie_config() -> dict[str, str]:
    """kie.ai GPT Image credentials (Grokbot / Unwire hero pipeline)."""
    load_env()
    key = os.getenv("KIE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("No KIE_API_KEY set. Paste the Grokbot kie.ai key into .env")
    return {
        "api_key": key,
        "base_url": os.getenv("KIE_BASE_URL", "https://api.kie.ai").rstrip("/"),
        "model": os.getenv("KIE_IMAGE_MODEL", "gpt-image-2-5-sunburst-text-to-image"),
    }


def topic_dir(topic: str) -> Path:
    path = PROJECT_ROOT / topic
    if not path.is_dir():
        raise FileNotFoundError(f"Topic directory not found: {path}")
    return path


def load_topic_config(topic: str) -> dict[str, Any]:
    cfg_path = topic_dir(topic) / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing config: {cfg_path}")
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"config.yaml must be a mapping: {cfg_path}")
    try:
        from hk_city.desk.settings_store import merge_topic_config

        return merge_topic_config(data)
    except Exception:
        return data


def data_root(topic: str) -> Path:
    return topic_dir(topic) / "data"
