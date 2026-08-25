from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from qsys.backtest_metrics import summarize
from qsys.portfolio import apply_risk
from qsys.types import ExecutionMode


@dataclass
class BacktestResult:
    equity: pd.Series
    returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, float] = field(default_factory=dict)
    extras: dict[str, pd.Series] = field(default_factory=dict)


def run_backtest(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    *,
    open_: pd.DataFrame | None = None,
    initial_cash: float = 100_000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    execution: ExecutionMode = "next_open",
    annualization: int = 252,
    risk: dict | None = None,
) -> BacktestResult:
    """Vectorized weight backtest. Target weights are shifted to avoid lookahead.

    weights[t] may use close[t]. Default execution holds those weights over
    the next bar's close-to-close return (research-grade, no same-bar fill).
    """
    close = close.sort_index().astype(float)
    weights = weights.reindex(index=close.index, columns=close.columns).fillna(0.0)
    if risk:
        weights = apply_risk(weights, **risk)

    if execution == "next_open":
        held = weights.shift(1).fillna(0.0)
    elif execution == "close":
        # Still shift by one: same-bar close fill would leak unless the
        # strategy is explicitly causal with a stricter lag.
        held = weights.shift(1).fillna(0.0)
    else:
        raise ValueError(f"Unknown execution mode: {execution}")

    if open_ is not None and execution == "next_open":
        px = open_.reindex_like(close).where(open_.reindex_like(close).notna(), close)
        asset_ret = px.pct_change().fillna(0.0)
    else:
        asset_ret = close.pct_change().fillna(0.0)
        px = close

    turnover = held.diff().abs().sum(axis=1)
    turnover = turnover.fillna(held.abs().sum(axis=1))
    cost = turnover * (commission + slippage)
    gross = (held * asset_ret).sum(axis=1)
    net = gross - cost

    equity = pd.Series(index=close.index, dtype=float)
    equity.iloc[0] = float(initial_cash)
    if len(close) > 1:
        equity.iloc[1:] = float(initial_cash) * (1.0 + net.iloc[1:]).cumprod()

    result = BacktestResult(
        equity=equity,
        returns=net,
        weights=held,
        turnover=turnover,
        trades=_turnover_to_trades(held, px),
        extras={"gross_returns": gross, "cost": cost},
    )
    result.metrics = summarize(result.returns, result.equity, annualization=annualization)
    return result


def _turnover_to_trades(held: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    delta = held.diff().fillna(held.iloc[0])
    rows = []
    for ts, row in delta.iterrows():
        for symbol, change in row.items():
            if abs(change) < 1e-12:
                continue
            px = price.loc[ts, symbol] if symbol in price.columns else np.nan
            rows.append(
                {
                    "datetime": ts,
                    "symbol": symbol,
                    "weight_change": float(change),
                    "price": float(px) if pd.notna(px) else np.nan,
                    "side": "buy" if change > 0 else "sell",
                }
            )
    return pd.DataFrame(rows)
