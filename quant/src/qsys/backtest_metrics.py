from __future__ import annotations

import numpy as np
import pandas as pd


def summarize(
    returns: pd.Series,
    equity: pd.Series,
    *,
    annualization: int = 252,
    risk_free: float = 0.0,
) -> dict[str, float]:
    rets = returns.dropna()
    if rets.empty:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "n_obs": 0.0,
        }
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    years = max(len(rets) / annualization, 1e-9)
    cagr = float((1.0 + total) ** (1.0 / years) - 1.0) if total > -1 else -1.0
    vol = float(rets.std(ddof=0) * np.sqrt(annualization))
    excess = rets - risk_free / annualization
    sharpe = float(excess.mean() / excess.std(ddof=0) * np.sqrt(annualization)) if excess.std(ddof=0) else 0.0
    dd = drawdown(equity)
    max_dd = float(dd.min())
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else 0.0
    win_rate = float((rets > 0).mean())
    return {
        "total_return": total,
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "win_rate": win_rate,
        "n_obs": float(len(rets)),
    }


def drawdown(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    return equity / peak - 1.0
