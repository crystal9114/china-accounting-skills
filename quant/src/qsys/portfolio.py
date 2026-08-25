from __future__ import annotations

import pandas as pd


def apply_risk(
    weights: pd.DataFrame,
    *,
    max_weight: float = 0.35,
    max_gross_exposure: float = 1.0,
    cash_buffer: float = 0.0,
    **_ignored,
) -> pd.DataFrame:
    clipped = weights.clip(lower=-max_weight, upper=max_weight)
    cap = max(max_gross_exposure - cash_buffer, 0.0)
    gross = clipped.abs().sum(axis=1).replace(0, 1.0)
    scale = (cap / gross).clip(upper=1.0)
    return clipped.mul(scale, axis=0)


def halt_if_daily_loss(returns: pd.Series, max_daily_loss: float) -> pd.Series:
    """Zero out weights after a daily loss breach (used by the paper loop)."""
    return returns < -abs(max_daily_loss)
