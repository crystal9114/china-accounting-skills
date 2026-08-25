from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Strategies return target weights in [-1, 1], columns = symbols."""

    name: str

    def __init__(self, **params):
        self.params = params

    @abstractmethod
    def generate(self, close: pd.DataFrame) -> pd.DataFrame:
        """Target weights using only information available on that bar."""


class SmaCrossover(Strategy):
    name = "sma"

    def generate(self, close: pd.DataFrame) -> pd.DataFrame:
        fast = int(self.params.get("fast", 20))
        slow = int(self.params.get("slow", 60))
        if fast >= slow:
            raise ValueError("sma fast window must be < slow window")
        fast_ma = close.rolling(fast, min_periods=fast).mean()
        slow_ma = close.rolling(slow, min_periods=slow).mean()
        long = (fast_ma > slow_ma).astype(float)
        n_long = long.sum(axis=1).replace(0, 1.0)
        return long.div(n_long, axis=0).fillna(0.0)


class Momentum(Strategy):
    name = "momentum"

    def generate(self, close: pd.DataFrame) -> pd.DataFrame:
        lookback = int(self.params.get("lookback", 63))
        top_k = int(self.params.get("top_k", 2))
        score = close.pct_change(lookback)
        rank = score.rank(axis=1, ascending=False, method="first")
        picked = (rank <= top_k) & score.notna()
        n = picked.sum(axis=1).replace(0, 1.0)
        return picked.astype(float).div(n, axis=0).fillna(0.0)


class MeanReversion(Strategy):
    name = "mean_reversion"

    def generate(self, close: pd.DataFrame) -> pd.DataFrame:
        window = int(self.params.get("window", 20))
        entry_z = float(self.params.get("entry_z", 1.0))
        z = (close - close.rolling(window).mean()) / close.rolling(window).std(ddof=0)
        # Long names that are cheap relative to their own window.
        long = (z <= -entry_z).astype(float)
        n = long.sum(axis=1).replace(0, 1.0)
        return long.div(n, axis=0).fillna(0.0)


class EqualWeight(Strategy):
    name = "equal_weight"

    def generate(self, close: pd.DataFrame) -> pd.DataFrame:
        weights = close.notna().astype(float)
        n = weights.sum(axis=1).replace(0, 1.0)
        return weights.div(n, axis=0)


STRATEGIES: dict[str, type[Strategy]] = {
    SmaCrossover.name: SmaCrossover,
    Momentum.name: Momentum,
    MeanReversion.name: MeanReversion,
    EqualWeight.name: EqualWeight,
}


def build_strategy(name: str, params: dict | None = None) -> Strategy:
    if name not in STRATEGIES:
        known = ", ".join(sorted(STRATEGIES))
        raise KeyError(f"Unknown strategy '{name}'. Available: {known}")
    return STRATEGIES[name](**(params or {}))
