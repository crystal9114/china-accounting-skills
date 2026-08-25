from __future__ import annotations

from typing import Literal

import pandas as pd

OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")
SourceName = Literal["yfinance", "akshare", "ccxt", "csv", "synthetic"]
ExecutionMode = Literal["next_open", "close"]
FillMode = Literal["next_open", "close"]
Side = Literal["buy", "sell"]


def ensure_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in OHLCV_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"OHLCV frame missing columns: {missing}")
    out = frame.copy()
    out.index = pd.to_datetime(out.index)
    out.index.name = "datetime"
    return out[list(OHLCV_COLUMNS)].sort_index()
