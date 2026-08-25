from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from qsys import __version__
from qsys.config import default_config_path
from qsys.pipeline import make_context, paper_broker, paper_step, pull_data, run_research, run_walkforward

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Personal quant stack (qsys)")
data_app = typer.Typer(no_args_is_help=True, help="Market data lake")
bt_app = typer.Typer(no_args_is_help=True, help="Research backtests")
paper_app = typer.Typer(no_args_is_help=True, help="Paper trading ledger")
app.add_typer(data_app, name="data")
app.add_typer(bt_app, name="backtest")
app.add_typer(paper_app, name="paper")

console = Console()


def _ctx(
    config: Optional[Path],
    source: Optional[str],
    symbols: Optional[str],
    strategy: Optional[str],
):
    syms = [s.strip() for s in symbols.split(",")] if symbols else None
    return make_context(config, source=source, symbols=syms, strategy=strategy)


@app.callback()
def _main() -> None:
    pass


@app.command()
def version() -> None:
    console.print(f"qsys {__version__}")


@app.command("demo")
def demo(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """End-to-end run on synthetic data: pull → backtest → paper step."""
    ctx = _ctx(config, "synthetic", None, None)
    pulled = pull_data(ctx)
    console.print(f"ingested {len(pulled)} symbols from synthetic")
    result, dest = run_research(ctx)
    _print_metrics(result.metrics)
    console.print(f"report → {dest}")
    snap = paper_step(ctx)
    console.print(f"paper equity {snap.equity:,.2f}  cash {snap.cash:,.2f}  halted={snap.halted}")


@data_app.command("pull")
def data_pull(
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    symbols: Optional[str] = typer.Option(None, "--symbols"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    ctx = _ctx(config, source, symbols, None)
    written = pull_data(ctx)
    console.print(f"wrote {len(written)} symbols to {ctx.cfg.paths.lake}")


@data_app.command("status")
def data_status(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    ctx = _ctx(config, None, None, None)
    rows = ctx.lake.list_symbols()
    table = Table(title="data lake")
    table.add_column("source")
    table.add_column("symbol")
    for src, sym in rows:
        table.add_row(src, sym)
    if not rows:
        console.print("lake is empty — run `qsys data pull` or `qsys demo`")
        return
    console.print(table)


@bt_app.command("run")
def backtest_run(
    strategy: Optional[str] = typer.Option(None, "--strategy"),
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    symbols: Optional[str] = typer.Option(None, "--symbols"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    ctx = _ctx(config, source, symbols, strategy)
    result, dest = run_research(ctx)
    _print_metrics(result.metrics)
    console.print(f"report → {dest}")


@bt_app.command("walk-forward")
def backtest_wf(
    train: int = typer.Option(252, "--train"),
    test: int = typer.Option(63, "--test"),
    strategy: Optional[str] = typer.Option(None, "--strategy"),
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    symbols: Optional[str] = typer.Option(None, "--symbols"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    ctx = _ctx(config, source, symbols, strategy)
    wf = run_walkforward(ctx, train=train, test=test)
    _print_metrics(wf.oos.metrics)
    console.print(wf.windows.tail().to_string(index=False))


@paper_app.command("step")
def paper_step_cmd(
    strategy: Optional[str] = typer.Option(None, "--strategy"),
    source: Optional[str] = typer.Option(None, "--source", "-s"),
    symbols: Optional[str] = typer.Option(None, "--symbols"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    ctx = _ctx(config, source, symbols, strategy)
    snap = paper_step(ctx)
    console.print(f"equity={snap.equity:,.2f} cash={snap.cash:,.2f} halted={snap.halted}")
    if not snap.positions.empty:
        console.print(snap.positions)


@paper_app.command("status")
def paper_status(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    ctx = _ctx(config, None, None, None)
    broker = paper_broker(ctx)
    console.print(broker.dump())


@app.command("dashboard")
def dashboard() -> None:
    """Launch the Streamlit cockpit (`pip install 'qsys[ui]'`)."""
    try:
        from streamlit.web import cli as stcli
    except ImportError as exc:
        raise typer.BadParameter("Install UI extra: pip install 'qsys[ui]'") from exc
    import sys

    app_path = Path(__file__).with_name("dashboard.py")
    sys.argv = ["streamlit", "run", str(app_path), "--browser.gatherUsageStats=false"]
    stcli.main()


@app.command("config-path")
def show_config_path() -> None:
    console.print(str(default_config_path()))


def _print_metrics(metrics: dict[str, float]) -> None:
    table = Table(title="metrics")
    table.add_column("metric")
    table.add_column("value", justify="right")
    for key, value in metrics.items():
        table.add_row(key, f"{value:,.4f}")
    console.print(table)


if __name__ == "__main__":
    app()
