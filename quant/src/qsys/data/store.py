from __future__ import annotations

from pathlib import Path

import pandas as pd

from qsys.types import OHLCV_COLUMNS, ensure_ohlcv


class ParquetLake:
    """Local market-data lake. One parquet file per source/symbol."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_symbol(self, symbol: str) -> str:
        return symbol.replace("/", "__")

    def _restore_symbol(self, encoded: str) -> str:
        return encoded.replace("__", "/", 1)

    def _path(self, source: str, symbol: str) -> Path:
        folder = self.root / f"source={source}" / f"symbol={self._safe_symbol(symbol)}"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "ohlcv.parquet"

    def write(self, source: str, symbol: str, frame: pd.DataFrame) -> Path:
        path = self._path(source, symbol)
        incoming = ensure_ohlcv(frame)
        if path.exists():
            existing = ensure_ohlcv(pd.read_parquet(path))
            merged = pd.concat([existing, incoming]).sort_index()
            incoming = merged[~merged.index.duplicated(keep="last")]
        incoming.to_parquet(path)
        return path

    def read(self, source: str, symbol: str) -> pd.DataFrame:
        path = self._path(source, symbol)
        if not path.exists():
            raise FileNotFoundError(f"No cached bars for {source}:{symbol} at {path}")
        frame = pd.read_parquet(path)
        frame.index = pd.to_datetime(frame.index)
        return ensure_ohlcv(frame)

    def has(self, source: str, symbol: str) -> bool:
        return self._path(source, symbol).exists()

    def list_symbols(self, source: str | None = None) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for parquet in self.root.glob("source=*/symbol=*/ohlcv.parquet"):
            src = parquet.parent.parent.name.split("=", 1)[1]
            encoded = parquet.parent.name.split("=", 1)[1]
            if source is None or src == source:
                found.append((src, self._restore_symbol(encoded)))
        return sorted(found)

    def load_panel(
        self,
        source: str,
        symbols: list[str],
        field: str = "close",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        if field not in OHLCV_COLUMNS:
            raise ValueError(f"Unknown field {field}")
        columns: dict[str, pd.Series] = {}
        for symbol in symbols:
            series = self.read(source, symbol)[field]
            if start:
                series = series[series.index >= pd.Timestamp(start)]
            if end:
                series = series[series.index <= pd.Timestamp(end)]
            columns[symbol] = series
        return pd.DataFrame(columns).sort_index().dropna(how="all")

    def load_ohlcv(
        self,
        source: str,
        symbols: list[str],
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            frame = self.read(source, symbol)
            if start:
                frame = frame[frame.index >= pd.Timestamp(start)]
            if end:
                frame = frame[frame.index <= pd.Timestamp(end)]
            out[symbol] = frame
        return out
