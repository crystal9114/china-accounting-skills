from __future__ import annotations

import pandas as pd

from qsys.data.ingest import ingest
from qsys.data.providers import SyntheticProvider
from qsys.paper import PaperBroker
from qsys.pipeline import make_context, paper_step, pull_data
from qsys.strategy import EqualWeight


def test_paper_step_opens_positions(cfg_path, tmp_path):
    ctx = make_context(cfg_path, strategy="equal_weight")
    pull_data(ctx)
    snap = paper_step(ctx)
    assert snap.equity > 0
    assert not snap.positions.empty
    assert snap.cash < ctx.cfg.paper.initial_cash
    broker = PaperBroker(tmp_path / "paper.sqlite")
    # independent broker starts empty
    assert broker.positions().empty


def test_ingest_writes_symbols(cfg_path):
    ctx = make_context(cfg_path)
    written = ingest(ctx.cfg)
    assert set(written) == {"AAA", "BBB", "CCC"}
    assert ctx.lake.has("synthetic", "AAA")


def test_equal_weight_strategy_direct(tmp_path):
    from qsys.data.providers import SyntheticProvider

    close = SyntheticProvider().fetch_many(["AAA", "BBB"], start="2021-01-01", end="2021-06-01")
    panel = pd.concat({k: v["close"] for k, v in close.items()}, axis=1)
    weights = EqualWeight().generate(panel)
    assert abs(weights.iloc[-1].sum() - 1.0) < 1e-9
