from __future__ import annotations

from qsys.data.providers import SyntheticProvider
from qsys.pipeline import make_context, pull_data, run_walkforward
from qsys.strategy import EqualWeight
from qsys.walkforward import walk_forward
import pandas as pd


def test_walk_forward_stitches_oos(cfg_path):
    ctx = make_context(cfg_path, strategy="equal_weight")
    pull_data(ctx)
    wf = run_walkforward(ctx, train=80, test=20)
    assert len(wf.windows) >= 1
    assert wf.oos.equity.iloc[-1] > 0
    assert "sharpe" in wf.oos.metrics


def test_walk_forward_direct():
    panel = SyntheticProvider().fetch_many(["AAA", "BBB"], start="2019-01-01", end="2021-12-31")
    close = pd.concat({k: v["close"] for k, v in panel.items()}, axis=1)
    wf = walk_forward(close, EqualWeight(), train=120, test=40, commission=0.0, slippage=0.0)
    assert wf.windows["oos_return"].notna().all()
