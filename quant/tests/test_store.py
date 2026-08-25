from __future__ import annotations

import pandas as pd

from qsys.data.providers import SyntheticProvider
from qsys.data.store import ParquetLake


def test_parquet_roundtrip_and_merge(tmp_path):
    lake = ParquetLake(tmp_path / "lake")
    first = SyntheticProvider(seed=1).fetch("AAA", start="2020-01-01", end="2020-02-01")
    lake.write("synthetic", "AAA", first.iloc[:10])
    lake.write("synthetic", "AAA", first.iloc[5:])
    loaded = lake.read("synthetic", "AAA")
    assert loaded.index.is_unique
    assert len(loaded) == len(first)
    assert list(lake.list_symbols()) == [("synthetic", "AAA")]


def test_load_panel_aligns_symbols(tmp_path):
    lake = ParquetLake(tmp_path / "lake")
    provider = SyntheticProvider(seed=2)
    for symbol in ("AAA", "BBB"):
        lake.write("synthetic", symbol, provider.fetch(symbol, start="2020-01-01", end="2020-03-01"))
    panel = lake.load_panel("synthetic", ["AAA", "BBB"], field="close")
    assert list(panel.columns) == ["AAA", "BBB"]
    assert panel.notna().all().all()
