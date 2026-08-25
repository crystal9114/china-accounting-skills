from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from qsys.backtest import BacktestResult, run_backtest
from qsys.config import AppConfig, load_config
from qsys.data.ingest import ingest
from qsys.data.store import ParquetLake
from qsys.paper import PaperBroker, PaperSnapshot
from qsys.report import write_report
from qsys.strategy import Strategy, build_strategy
from qsys.walkforward import WalkForwardResult, walk_forward


@dataclass
class RunContext:
    cfg: AppConfig
    lake: ParquetLake
    strategy: Strategy
    source: str
    symbols: list[str]


def make_context(
    config_path: Path | None = None,
    *,
    source: str | None = None,
    symbols: list[str] | None = None,
    strategy: str | None = None,
) -> RunContext:
    cfg = load_config(config_path)
    src = source or cfg.universe.source
    syms = symbols or list(cfg.universe.symbols)
    strat = build_strategy(strategy or cfg.strategy.name, cfg.strategy.params)
    return RunContext(
        cfg=cfg,
        lake=ParquetLake(cfg.paths.lake),
        strategy=strat,
        source=src,
        symbols=syms,
    )


def pull_data(ctx: RunContext) -> list[str]:
    return ingest(ctx.cfg, source=ctx.source, symbols=ctx.symbols)


def load_close(ctx: RunContext) -> pd.DataFrame:
    return ctx.lake.load_panel(
        ctx.source,
        ctx.symbols,
        field="close",
        start=ctx.cfg.universe.start,
        end=ctx.cfg.universe.end,
    )


def run_research(ctx: RunContext) -> tuple[BacktestResult, Path]:
    close = load_close(ctx)
    if close.empty:
        raise RuntimeError("No close prices in the lake. Run `qsys data pull` first.")
    weights = ctx.strategy.generate(close)
    result = run_backtest(
        close,
        weights,
        initial_cash=ctx.cfg.backtest.initial_cash,
        commission=ctx.cfg.backtest.commission,
        slippage=ctx.cfg.backtest.slippage,
        execution=ctx.cfg.backtest.execution,  # type: ignore[arg-type]
        annualization=ctx.cfg.backtest.annualization,
        risk=ctx.cfg.risk.model_dump(),
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = ctx.cfg.paths.reports / f"{ctx.strategy.name}-{stamp}"
    write_report(result, dest)
    latest = ctx.cfg.paths.reports / "latest"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    try:
        latest.symlink_to(dest.name, target_is_directory=True)
    except OSError:
        pass
    return result, dest


def run_walkforward(ctx: RunContext, train: int = 252, test: int = 63) -> WalkForwardResult:
    close = load_close(ctx)
    return walk_forward(
        close,
        ctx.strategy,
        train=train,
        test=test,
        initial_cash=ctx.cfg.backtest.initial_cash,
        commission=ctx.cfg.backtest.commission,
        slippage=ctx.cfg.backtest.slippage,
        annualization=ctx.cfg.backtest.annualization,
        risk=ctx.cfg.risk.model_dump(),
    )


def paper_broker(ctx: RunContext) -> PaperBroker:
    return PaperBroker(ctx.cfg.paths.paper_db, initial_cash=ctx.cfg.paper.initial_cash)


def paper_step(ctx: RunContext) -> PaperSnapshot:
    close = load_close(ctx)
    broker = paper_broker(ctx)
    return broker.step(
        ctx.strategy,
        close,
        commission=ctx.cfg.paper.commission,
        slippage=ctx.cfg.paper.slippage,
        risk=ctx.cfg.risk.model_dump(),
    )
