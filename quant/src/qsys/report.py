from __future__ import annotations

from pathlib import Path

import pandas as pd

from qsys.backtest import BacktestResult


def write_report(result: BacktestResult, dest: Path) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    metrics = pd.Series(result.metrics, name="value")
    metrics.to_csv(dest / "metrics.csv")
    result.equity.rename("equity").to_csv(dest / "equity.csv")
    result.returns.rename("return").to_csv(dest / "returns.csv")
    result.weights.to_csv(dest / "weights.csv")
    if not result.trades.empty:
        result.trades.to_csv(dest / "trades.csv", index=False)

    html_path = dest / "tearsheet.html"
    try:
        import quantstats as qs

        qs.reports.html(
            result.returns.fillna(0.0),
            output=str(html_path),
            title="qsys tearsheet",
            download_filename=str(html_path),
        )
    except Exception:
        html_path.write_text(_fallback_html(result), encoding="utf-8")
    return dest


def _fallback_html(result: BacktestResult) -> str:
    rows = "".join(
        f"<tr><th>{key}</th><td>{value:.4f}</td></tr>" for key, value in result.metrics.items()
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>qsys report</title></head>
<body>
<h1>qsys backtest report</h1>
<p>Install <code>qsys[report]</code> for a QuantStats tearsheet.</p>
<table>{rows}</table>
</body></html>
"""
