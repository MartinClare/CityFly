"""Official property / rate series: RVD CSVs and HKMA HIBOR API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any

import pandas as pd
import requests

from common.base_collector import BaseCollector

logger = logging.getLogger(__name__)
TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CityFlyBot/0.1"


class PropertyDataCollector(BaseCollector):
    name = "property_data"

    def fetch(self) -> dict[str, Any]:
        group = (self.config.get("collectors") or {}).get(self.name) or {}
        series: list[dict[str, Any]] = []
        for spec in group.get("series") or []:
            series.append(_fetch_series(spec))
        return {
            "as_of": self.storage.as_of,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "series": series,
        }


def _fetch_series(spec: dict[str, Any]) -> dict[str, Any]:
    name = spec.get("name", spec.get("url", "series"))
    url = spec["url"]
    kind = (spec.get("kind") or "csv").lower()
    out: dict[str, Any] = {
        "name": name,
        "url": url,
        "tier": spec.get("tier", 1),
        "policy": spec.get("policy", "official_api"),
    }
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        if kind == "hkma_json":
            out.update(_parse_hkma(resp.json(), spec))
        else:
            out.update(_parse_tabular(resp.content, spec))
    except Exception as exc:
        logger.warning("Property series %s failed: %s", name, exc)
        out["error"] = str(exc)
    return out


def _parse_hkma(payload: Any, spec: dict[str, Any]) -> dict[str, Any]:
    records = []
    if isinstance(payload, dict):
        records = ((payload.get("result") or {}).get("records")) or []
    if not records:
        return {"error": "no HKMA records", "latest": None}
    key = spec.get("value_field") or "ir_overnight"
    date_field = spec.get("date_field") or "end_of_day"
    latest = records[0]
    prev = records[1] if len(records) > 1 else None
    latest_val = _to_float(latest.get(key))
    prev_val = _to_float(prev.get(key)) if prev else None
    change = None
    if latest_val is not None and prev_val not in (None, 0):
        change = round(latest_val - prev_val, 4)
    return {
        "latest": {
            "date": latest.get(date_field),
            "value": latest_val,
            "change": change,
            "unit": spec.get("unit", "%"),
        },
        "sample": records[:5],
    }


def _parse_tabular(content: bytes, spec: dict[str, Any]) -> dict[str, Any]:
    df = _read_table(content)
    if df is None or df.empty:
        return {"error": "empty table", "latest": None}
    numeric = df.select_dtypes(include="number")
    date_col = _guess_date_col(df)
    value_col = spec.get("value_column")
    if value_col and value_col in df.columns:
        series = pd.to_numeric(df[value_col], errors="coerce")
    elif not numeric.empty:
        series = numeric.iloc[:, 0]
    else:
        series = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    clean = series.dropna()
    if clean.empty:
        return {"error": "no numeric column", "columns": [str(c) for c in df.columns[:12]]}
    latest_val = float(clean.iloc[-1])
    prev_val = float(clean.iloc[-2]) if len(clean) > 1 else None
    yoy_val = float(clean.iloc[-13]) if len(clean) > 12 else None
    latest_date = None
    if date_col is not None:
        try:
            latest_date = str(df.loc[clean.index[-1], date_col])
        except Exception:
            latest_date = None
    mom = None
    yoy = None
    if prev_val not in (None, 0):
        mom = round((latest_val / prev_val - 1) * 100, 2)
    if yoy_val not in (None, 0):
        yoy = round((latest_val / yoy_val - 1) * 100, 2)
    return {
        "latest": {
            "date": latest_date,
            "value": latest_val,
            "mom_pct": mom,
            "yoy_pct": yoy,
            "unit": spec.get("unit", ""),
        },
        "rows": int(len(df)),
        "columns": [str(c) for c in df.columns[:12]],
    }


def _read_table(content: bytes) -> pd.DataFrame | None:
    for reader in (
        lambda: pd.read_csv(BytesIO(content)),
        lambda: pd.read_csv(StringIO(content.decode("utf-8", errors="ignore"))),
        lambda: pd.read_excel(BytesIO(content)),
        lambda: pd.read_csv(BytesIO(content), sep="\t"),
    ):
        try:
            df = reader()
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


def _guess_date_col(df: pd.DataFrame) -> Any | None:
    for col in df.columns:
        name = str(col).lower()
        if any(tok in name for tok in ("date", "month", "year", "period", "end_of", "年月")):
            return col
    return df.columns[0]


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    import logging
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO)
    from common.config import load_topic_config
    from common.storage import TopicStorage

    print(PropertyDataCollector(TopicStorage("hk_city"), load_topic_config("hk_city")).run())
