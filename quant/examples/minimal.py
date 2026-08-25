"""Minimal research loop without the CLI."""

import pandas as pd

from qsys.backtest import run_backtest
from qsys.data.providers import SyntheticProvider
from qsys.strategy import SmaCrossover


def main() -> None:
    provider = SyntheticProvider(seed=3)
    frames = provider.fetch_many(["AAA", "BBB", "CCC"], start="2019-01-01", end="2023-12-31")
    panel = pd.DataFrame({symbol: frame["close"] for symbol, frame in frames.items()}).dropna()
    weights = SmaCrossover(fast=20, slow=60).generate(panel)
    result = run_backtest(panel, weights)
    print(result.metrics)


if __name__ == "__main__":
    main()
