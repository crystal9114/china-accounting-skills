from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import pandas as pd

from qsys.config import AppConfig
from qsys.types import ensure_ohlcv


class ProviderError(RuntimeError):
    pass


class DataProvider(ABC):
    name: str

    @abstractmethod
    def fetch(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Return OHLCV indexed by datetime."""

    def fetch_many(
        self,
        symbols: list[str],
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ) -> dict[str, pd.DataFrame]:
        return {
            symbol: ensure_ohlcv(self.fetch(symbol, start=start, end=end, **kwargs))
            for symbol in symbols
        }


class SyntheticProvider(DataProvider):
    """Deterministic demo prices so the stack runs with zero API keys."""

    name = "synthetic"

    def __init__(self, seed: int = 7):
        self.seed = seed

    def fetch(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        start_ts = pd.Timestamp(start or "2018-01-01")
        end_ts = pd.Timestamp(end or pd.Timestamp.today().normalize())
        index = pd.bdate_range(start_ts, end_ts, freq="C")
        rng = np.random.default_rng(self.seed + sum(ord(ch) for ch in symbol))
        drift = 0.00025 + (sum(ord(ch) for ch in symbol) % 5) * 0.00005
        rets = rng.normal(drift, 0.012, size=len(index))
        close = 100 * np.exp(np.cumsum(rets))
        open_ = np.concatenate([[close[0]], close[:-1]])
        high = np.maximum(open_, close) * (1 + rng.uniform(0.0, 0.008, size=len(index)))
        low = np.minimum(open_, close) * (1 - rng.uniform(0.0, 0.008, size=len(index)))
        volume = rng.integers(200_000, 800_000, size=len(index))
        return ensure_ohlcv(
            pd.DataFrame(
                {
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                },
                index=index,
            )
        )


class CsvProvider(DataProvider):
    name = "csv"

    def __init__(self, csv_dir: Path):
        self.csv_dir = Path(csv_dir)

    def fetch(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        path = self.csv_dir / f"{symbol.replace('/', '_')}.csv"
        if not path.exists():
            raise ProviderError(f"CSV not found: {path}")
        frame = pd.read_csv(path, parse_dates=[0], index_col=0)
        frame = ensure_ohlcv(frame)
        if start:
            frame = frame[frame.index >= pd.Timestamp(start)]
        if end:
            frame = frame[frame.index <= pd.Timestamp(end)]
        return frame


class YahooProvider(DataProvider):
    name = "yfinance"

    def fetch(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ProviderError("Install the US extra: pip install 'qsys[us]'") from exc
        hist = yf.download(
            symbol,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            group_by="column",
        )
        if hist.empty:
            raise ProviderError(f"yfinance returned no rows for {symbol}")
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)
        hist = hist.rename(columns=str.lower)
        hist = hist.rename(columns={"adj close": "close"})
        return ensure_ohlcv(hist)


class AkshareProvider(DataProvider):
    name = "akshare"

    def fetch(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        try:
            import akshare as ak
        except ImportError as exc:
            raise ProviderError("Install the China extra: pip install 'qsys[china]'") from exc
        adjust = kwargs.get("adjust", "qfq")
        start_s = pd.Timestamp(start or "20180101").strftime("%Y%m%d")
        end_s = pd.Timestamp(end or pd.Timestamp.today()).strftime("%Y%m%d")
        raw = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_s,
            end_date=end_s,
            adjust="" if adjust in {"none", "", None} else adjust,
        )
        if raw is None or raw.empty:
            raise ProviderError(f"akshare returned no rows for {symbol}")
        rename = {
            "日期": "datetime",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
        }
        frame = raw.rename(columns=rename)
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame = frame.set_index("datetime")
        return ensure_ohlcv(frame)


class CcxtProvider(DataProvider):
    name = "ccxt"

    def __init__(self, exchange: str = "binance", timeframe: str = "1d"):
        self.exchange_id = exchange
        self.timeframe = timeframe

    def fetch(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        try:
            import ccxt
        except ImportError as exc:
            raise ProviderError("Install the crypto extra: pip install 'qsys[crypto]'") from exc
        if not hasattr(ccxt, self.exchange_id):
            raise ProviderError(f"Unknown ccxt exchange: {self.exchange_id}")
        exchange = getattr(ccxt, self.exchange_id)({"enableRateLimit": True})
        since = int(pd.Timestamp(start or "2018-01-01").timestamp() * 1000)
        end_ms = int(pd.Timestamp(end or pd.Timestamp.today()).timestamp() * 1000)
        rows: list[list] = []
        while since < end_ms:
            batch = exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, since=since, limit=1000)
            if not batch:
                break
            rows.extend(batch)
            since = batch[-1][0] + 1
            if len(batch) < 50:
                break
        if not rows:
            raise ProviderError(f"ccxt returned no rows for {symbol}")
        frame = pd.DataFrame(rows, columns=["datetime", "open", "high", "low", "close", "volume"])
        frame["datetime"] = pd.to_datetime(frame["datetime"], unit="ms")
        frame = frame.set_index("datetime")
        if end:
            frame = frame[frame.index <= pd.Timestamp(end)]
        return ensure_ohlcv(frame[~frame.index.duplicated(keep="last")])


def get_provider(source: str, cfg: AppConfig | None = None) -> DataProvider:
    cfg = cfg or AppConfig()
    if source == "synthetic":
        return SyntheticProvider()
    if source == "csv":
        return CsvProvider(cfg.data.csv_dir)
    if source == "yfinance":
        return YahooProvider()
    if source == "akshare":
        return AkshareProvider()
    if source == "ccxt":
        return CcxtProvider(cfg.data.ccxt_exchange, cfg.data.ccxt_timeframe)
    raise ProviderError(f"Unknown data source: {source}")
