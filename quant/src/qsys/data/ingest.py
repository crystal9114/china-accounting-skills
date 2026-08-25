from __future__ import annotations

from qsys.config import AppConfig
from qsys.data.providers import get_provider
from qsys.data.store import ParquetLake


def ingest(
    cfg: AppConfig,
    source: str | None = None,
    symbols: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    **kwargs,
) -> list[str]:
    source = source or cfg.universe.source or cfg.data.default_source
    symbols = symbols or list(cfg.universe.symbols)
    start = start or cfg.universe.start
    end = end or cfg.universe.end
    provider = get_provider(source, cfg)
    lake = ParquetLake(cfg.paths.lake)
    written: list[str] = []
    extra = dict(kwargs)
    if source == "akshare":
        extra.setdefault("adjust", cfg.universe.adjust)
    frames = provider.fetch_many(symbols, start=start, end=end, **extra)
    for symbol, frame in frames.items():
        if frame.empty:
            continue
        lake.write(source, symbol, frame)
        written.append(symbol)
    return written
