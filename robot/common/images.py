"""kie.ai GPT Image 2.5 client (Grokbot / Unwire hero step)."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from common.config import get_kie_config

logger = logging.getLogger(__name__)

CREATE_PATH = "/api/v1/jobs/createTask"
STATUS_PATH = "/api/v1/jobs/recordInfo"
POLL_SEC = 4
MAX_POLLS = 45
DOWNLOAD_TIMEOUT = 60


def available() -> bool:
    try:
        get_kie_config()
        return True
    except RuntimeError:
        return False


_SKIP_IMG = re.compile(
    r"(logo|icon|banner|button|spacer|pixel|sprite|avatar|favicon|wcag|iso9001|iso14001|brand-hk|lang\.png|hotline|erb\.png|pfa_)",
    re.I,
)
_PREFER_IMG = re.compile(r"(attachment|map|plan|diagram|figure|og:image)", re.I)


def fetch_press_image(page_urls: list[str], dest: Path) -> dict[str, Any] | None:
    """Download the first usable official/press image. Skip logos and tiny assets."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CityFlyBot/0.1",
            "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
        }
    )
    for page in page_urls:
        if not page or not page.startswith("http"):
            continue
        try:
            resp = session.get(page, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.info("Press page failed %s: %s", page, exc)
            continue
        candidates = _image_candidates(page, resp.text, resp.headers.get("content-type", ""))
        for img_url, kind in candidates:
            try:
                img = session.get(img_url, timeout=DOWNLOAD_TIMEOUT)
                img.raise_for_status()
                if len(img.content) < 20_000:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(img.content)
                return {
                    "ok": True,
                    "path": str(dest),
                    "source_url": img_url,
                    "credit": page,
                    "visual_kind": kind,
                    "ai_generated": False,
                }
            except Exception as exc:
                logger.info("Press image failed %s: %s", img_url, exc)
    return None


def _image_candidates(page: str, html: str, content_type: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    soup = BeautifulSoup(html, "lxml")
    og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og and og.get("content"):
        found.append((urljoin(page, og["content"]), "og_image"))
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if _SKIP_IMG.search(src) or src.startswith("data:"):
            continue
        full = urljoin(page, src)
        kind = "official_map" if _PREFER_IMG.search(src) or "attachment" in src.lower() else "press_photo"
        if kind == "official_map":
            found.insert(0, (full, kind))
        else:
            found.append((full, kind))
    # unique preserve order
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for url, kind in found:
        if url in seen:
            continue
        seen.add(url)
        out.append((url, kind))
    return out


def generate_illustration(prompt: str, dest: Path) -> dict[str, Any]:
    """Create a labelled editorial illustration. Never treat as a real photograph."""
    cfg = get_kie_config()
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    full_prompt = (
        "Editorial magazine illustration / conceptual diagram for a Hong Kong city magazine. "
        "Not a photograph. Not a real street, construction site, or project rendering. "
        "Clear, prestige visual, map-or-diagram energy, muted print palette. "
        "Constructive and forward-looking: corridors opening, innovation, civic energy. Not grim, not satirical. "
        f"{prompt}"
    )
    payload = {
        "model": cfg["model"],
        "input": {
            "prompt": full_prompt,
            "aspect_ratio": "16:9",
            "resolution": "2K",
        },
    }
    create_url = f"{cfg['base_url']}{CREATE_PATH}"
    resp = requests.post(create_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    task_id = _extract_task_id(body)
    if not task_id:
        raise RuntimeError(f"kie.ai createTask missing taskId: {body}")

    image_url = _poll_result(cfg["base_url"], headers, task_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = requests.get(image_url, timeout=DOWNLOAD_TIMEOUT)
    img.raise_for_status()
    dest.write_bytes(img.content)
    return {
        "ok": True,
        "task_id": task_id,
        "path": str(dest),
        "source_url": image_url,
        "model": cfg["model"],
        "visual_kind": "illustration",
        "ai_generated": True,
    }


def _extract_task_id(body: dict[str, Any]) -> str | None:
    data = body.get("data") if isinstance(body, dict) else None
    if isinstance(data, dict):
        return data.get("taskId") or data.get("task_id") or data.get("id")
    return body.get("taskId") or body.get("task_id")


def _poll_result(base: str, headers: dict[str, str], task_id: str) -> str:
    url = f"{base}{STATUS_PATH}"
    last: Any = None
    for _ in range(MAX_POLLS):
        resp = requests.get(url, headers=headers, params={"taskId": task_id}, timeout=30)
        resp.raise_for_status()
        last = resp.json()
        data = last.get("data") if isinstance(last, dict) else last
        state = ""
        if isinstance(data, dict):
            state = str(data.get("state") or data.get("status") or "").lower()
            if state in {"success", "succeed", "completed", "done"}:
                url_found = _first_result_url(data)
                if url_found:
                    return url_found
            if state in {"fail", "failed", "error"}:
                raise RuntimeError(f"kie.ai task failed: {data}")
        time.sleep(POLL_SEC)
    raise RuntimeError(f"kie.ai task timed out: {last}")


def _first_result_url(data: dict[str, Any]) -> str | None:
    raw = data.get("resultJson") or data.get("result_json")
    parsed: Any = raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
    if isinstance(parsed, dict):
        urls = parsed.get("resultUrls") or parsed.get("result_urls") or []
        if urls:
            return urls[0]
    for key in ("resultUrls", "resultUrl", "url", "imageUrl"):
        val = data.get(key)
        if isinstance(val, list) and val:
            return val[0]
        if isinstance(val, str) and val.startswith("http"):
            return val
    return None


def looks_like_url(value: str) -> bool:
    try:
        return urlparse(value).scheme in {"http", "https"}
    except Exception:
        return False
