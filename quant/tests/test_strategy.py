from __future__ import annotations

import numpy as np
import pandas as pd

from qsys.strategy import EqualWeight, MeanReversion, Momentum, SmaCrossover, build_strategy


def _close():
    idx = pd.bdate_range("2020-01-01", periods=80)
    aaa = pd.Series(np.linspace(100, 140, len(idx)), index=idx)
    bbb = pd.Series(np.linspace(100, 90, len(idx)), index=idx)
    return pd.DataFrame({"AAA": aaa, "BBB": bbb})


def test_sma_goes_long_uptrend_only():
    weights = SmaCrossover(fast=5, slow=20).generate(_close())
    tail = weights.iloc[-1]
    assert tail["AAA"] > 0
    assert tail["BBB"] == 0


def test_momentum_picks_top_k():
    weights = Momentum(lookback=10, top_k=1).generate(_close())
    tail = weights.iloc[-1]
    assert tail["AAA"] == 1.0
    assert tail["BBB"] == 0.0


def test_equal_weight_and_registry():
    close = _close()
    weights = EqualWeight().generate(close)
    assert np.allclose(weights.iloc[-1].sum(), 1.0)
    strategy = build_strategy("mean_reversion", {"window": 10, "entry_z": 0.5})
    assert isinstance(strategy, MeanReversion)
    out = strategy.generate(close)
    assert out.shape == close.shape
