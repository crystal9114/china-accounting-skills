from __future__ import annotations

import numpy as np
import pandas as pd

from qsys.backtest import run_backtest
from qsys.strategy import EqualWeight, SmaCrossover


def _trend_prices(n=60):
    idx = pd.bdate_range("2020-01-01", periods=n)
    close = pd.DataFrame(
        {
            "AAA": np.linspace(100, 160, n),
            "BBB": np.linspace(100, 80, n),
        },
        index=idx,
    )
    return close


def test_first_bar_is_flat():
    close = _trend_prices()
    weights = pd.DataFrame(1.0, index=close.index, columns=close.columns)
    result = run_backtest(close, weights, commission=0.0, slippage=0.0)
    assert result.weights.iloc[0].sum() == 0.0
    assert result.equity.iloc[0] == 100_000.0


def test_commission_reduces_equity():
    close = _trend_prices()
    weights = EqualWeight().generate(close)
    cheap = run_backtest(close, weights, commission=0.0, slippage=0.0)
    expensive = run_backtest(close, weights, commission=0.01, slippage=0.0)
    assert expensive.equity.iloc[-1] < cheap.equity.iloc[-1]


def test_sma_on_uptrend_makes_money_with_no_costs():
    close = _trend_prices(120)
    weights = SmaCrossover(fast=5, slow=20).generate(close)
    result = run_backtest(close, weights, commission=0.0, slippage=0.0)
    assert result.equity.iloc[-1] > result.equity.iloc[0]
    assert result.metrics["n_obs"] == len(close)
