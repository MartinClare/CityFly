"""kie.ai GPT Image 2.5 client (Grokbot / Unwire hero step)."""

from __future__ import annotations

import json
import logging
import re
import struct
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
MIN_BYTES = 20_000
# Flat brand marks (e.g. Intel 2-colour lockups) compress tiny for their pixel area.
MAX_FLAT_BYTES_PER_PIXEL = 0.06


def available() -> bool:
    try:
        get_kie_config()
        return True
    except RuntimeError:
        return False


_SKIP_IMG = re.compile(
    r"("
    r"logo|wordmark|brandmark|lockup|sponsor|partner[-_]?logo|"
    r"icon|banner|button|spacer|pixel|sprite|avatar|favicon|"
    r"wcag|iso9001|iso14001|brand-hk|lang\.png|hotline|erb\.png|pfa_|"
    r"[-_/]2c[-_]|[-_]2[-_]?color"
    r")",
    re.I,
)
_PREFER_IMG = re.compile(r"(attachment|map|plan|diagram|figure|og:image)", re.I)


def _is_logo_url(url: str) -> bool:
    return bool(url and _SKIP_IMG.search(url))


def _png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in {0xC0, 0xC1, 0xC2}:  # SOF0/1/2
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        if marker in {0xD9, 0xDA}:
            break
        if i + 3 >= len(data):
            break
        seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + seg_len
    return None


def _image_dims(data: bytes) -> tuple[int, int] | None:
    return _png_size(data) or _jpeg_size(data)


def _looks_like_logo_bytes(data: bytes, url: str = "") -> bool:
    """Reject brand lockups: logo-ish URLs, or huge canvases with almost no pixel data."""
    if _is_logo_url(url):
        return True
    dims = _image_dims(data)
    if not dims:
        return False
    w, h = dims
    if w < 1 or h < 1:
        return True
    pixels = w * h
    # Tiny icons / brand marks even when the file clears MIN_BYTES.
    if max(w, h) < 400 and min(w, h) < 200:
        return True
    bpp = len(data) / pixels
    if pixels >= 400_000 and bpp < MAX_FLAT_BYTES_PER_PIXEL:
        logger.info(
            "Rejecting flat brand image %sx%s (%.4f bytes/px) %s",
            w,
            h,
            bpp,
            (url or "")[:120],
        )
        return True
    return False


def _accept_image_bytes(data: bytes, *, url: str = "", ctype: str = "") -> bool:
    if len(data) < MIN_BYTES:
        return False
    ctype = (ctype or "").lower()
    if ctype and not ctype.startswith("image/") and "octet-stream" not in ctype:
        return False
    if _looks_like_logo_bytes(data, url):
        return False
    return True


def download_direct_image(
    image_url: str,
    dest: Path,
    *,
    credit: str | None = None,
) -> dict[str, Any] | None:
    """Download a known hero URL (e.g. from RSS media:content). Skip tiny/logo assets."""
    if not image_url or not str(image_url).startswith("http"):
        return None
    if _is_logo_url(image_url):
        return None
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CityFlyBot/0.1",
            "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
        }
    )
    try:
        img = session.get(image_url, timeout=DOWNLOAD_TIMEOUT)
        img.raise_for_status()
        if not _accept_image_bytes(
            img.content, url=image_url, ctype=img.headers.get("content-type", "")
        ):
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(img.content)
        return {
            "ok": True,
            "path": str(dest),
            "source_url": image_url,
            "credit": credit or image_url,
            "visual_kind": "rss_image",
            "ai_generated": False,
        }
    except Exception as exc:
        logger.info("Direct image failed %s: %s", image_url, exc)
        return None


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
                if not _accept_image_bytes(
                    img.content, url=img_url, ctype=img.headers.get("content-type", "")
                ):
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
        og_url = urljoin(page, og["content"])
        if not _is_logo_url(og_url):
            found.append((og_url, "og_image"))
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src or src.startswith("data:") or _is_logo_url(src):
            continue
        full = urljoin(page, src)
        if _is_logo_url(full):
            continue
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
