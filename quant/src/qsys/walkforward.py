from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from qsys.backtest import BacktestResult, run_backtest
from qsys.strategy import Strategy


@dataclass
class WalkForwardResult:
    oos: BacktestResult
    windows: pd.DataFrame


def walk_forward(
    close: pd.DataFrame,
    strategy: Strategy,
    *,
    train: int = 252,
    test: int = 63,
    step: int | None = None,
    open_: pd.DataFrame | None = None,
    **backtest_kwargs,
) -> WalkForwardResult:
    """Rolling IS/OOS backtest. Strategy params stay fixed; only the evaluation window rolls."""
    step = step or test
    index = close.index
    records = []
    oos_returns = []
    oos_equity_parts = []
    last_equity = float(backtest_kwargs.get("initial_cash", 100_000.0))

    start = 0
    while True:
        train_end = start + train
        test_end = train_end + test
        if test_end > len(index):
            break
        window = close.iloc[start:test_end]
        weights = strategy.generate(window)
        result = run_backtest(
            window,
            weights,
            open_=None if open_ is None else open_.iloc[start:test_end],
            **backtest_kwargs,
        )
        test_slice = result.returns.iloc[train:]
        oos_returns.append(test_slice)
        # stitch equity from the last OOS level
        growth = (1.0 + test_slice).cumprod()
        part = last_equity * growth
        oos_equity_parts.append(part)
        last_equity = float(part.iloc[-1])
        records.append(
            {
                "train_start": index[start],
                "train_end": index[train_end - 1],
                "test_start": index[train_end],
                "test_end": index[test_end - 1],
                "oos_return": float((1.0 + test_slice).prod() - 1.0),
            }
        )
        start += step

    if not oos_returns:
        raise ValueError("Not enough history for walk-forward windows")

    oos_ret = pd.concat(oos_returns)
    oos_eq = pd.concat(oos_equity_parts)
    from qsys.backtest_metrics import summarize

    oos_result = BacktestResult(
        equity=oos_eq,
        returns=oos_ret,
        weights=pd.DataFrame(),
        turnover=pd.Series(dtype=float),
        trades=pd.DataFrame(),
        metrics=summarize(oos_ret, oos_eq, annualization=backtest_kwargs.get("annualization", 252)),
    )
    return WalkForwardResult(oos=oos_result, windows=pd.DataFrame.from_records(records))
