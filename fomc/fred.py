"""Minimal FRED access for the macro context ribbon.

Copied from ``us_oil_sensitive/us_svar/data.py`` (the verified ``_env_key`` +
``_fred_observations`` pattern) so this project stays self-contained. Cached
monthly under ``data/raw/fred``; the build degrades gracefully if offline.
"""
from __future__ import annotations

import io
import os
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from . import config

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"


def _env_key(name: str, signup_url: str) -> str:
    key = os.environ.get(name, "").strip()
    if not key:
        env_path = config.PROJECT_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(name) and "=" in line:
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise RuntimeError(f"{name} not set. Put {name}=<key> in {config.PROJECT_ROOT / '.env'}. "
                           f"Free key: {signup_url}")
    return key


def fred_api_key() -> str:
    return _env_key("FRED_API_KEY", "https://fred.stlouisfed.org/docs/api/api_key.html")


def _observations(series_id: str, *, force_refresh: bool = False) -> pd.DataFrame:
    stamp = pd.Timestamp.now().strftime("%Y-%m")
    cache = config.FRED_DIR / f"{series_id}_{stamp}.csv"
    if cache.exists() and not force_refresh:
        return pd.read_csv(cache, parse_dates=["date"])
    params = urllib.parse.urlencode(
        {"series_id": series_id, "api_key": fred_api_key(), "file_type": "json"}
    )
    req = urllib.request.Request(f"{FRED_API_URL}?{params}",
                                 headers={"User-Agent": "fomc-reaction-functions/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = pd.read_json(io.BytesIO(resp.read()))
    obs = pd.json_normalize(payload["observations"])
    raw = pd.DataFrame({"date": pd.to_datetime(obs["date"]),
                        "value": pd.to_numeric(obs["value"], errors="coerce")})
    config.FRED_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_csv(cache, index=False)
    return raw


def latest(series_id: str) -> tuple[float, str] | None:
    """(value, date) of the last non-NaN observation, or None if unavailable."""
    try:
        raw = _observations(series_id).dropna(subset=["value"])
    except Exception as exc:  # offline / no key -> ribbon just omits the value
        print(f"  [fred] {series_id} unavailable: {exc}")
        return None
    if raw.empty:
        return None
    row = raw.iloc[-1]
    return float(row["value"]), pd.Timestamp(row["date"]).strftime("%b %Y")


def macro_ribbon() -> dict:
    """Effective funds rate, core PCE YoY, unemployment rate for the header."""
    out: dict = {}
    dff = latest("DFF")
    if dff:
        out["funds"] = {"value": round(dff[0], 2), "asof": dff[1]}
    unrate = latest("UNRATE")
    if unrate:
        out["unrate"] = {"value": round(unrate[0], 1), "asof": unrate[1]}
    # Core PCE YoY from the price index.
    try:
        raw = _observations("PCEPILFE").dropna(subset=["value"]).set_index("date")["value"]
        yoy = raw.pct_change(12).dropna() * 100
        if not yoy.empty:
            out["core_pce_yoy"] = {"value": round(float(yoy.iloc[-1]), 2),
                                   "asof": pd.Timestamp(yoy.index[-1]).strftime("%b %Y")}
    except Exception as exc:
        print(f"  [fred] PCEPILFE unavailable: {exc}")
    return out
