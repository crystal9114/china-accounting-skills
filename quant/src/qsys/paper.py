from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from qsys.portfolio import apply_risk, halt_if_daily_loss
from qsys.strategy import Strategy


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    quantity REAL NOT NULL,
    avg_price REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    commission REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS equity (
    ts TEXT PRIMARY KEY,
    cash REAL NOT NULL,
    equity REAL NOT NULL,
    note TEXT
);
"""


@dataclass
class PaperSnapshot:
    cash: float
    equity: float
    positions: pd.DataFrame
    halted: bool


class PaperBroker:
    def __init__(self, db_path: Path, initial_cash: float = 100_000.0):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initial_cash = float(initial_cash)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            row = conn.execute("SELECT value FROM meta WHERE key = 'cash'").fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO meta(key, value) VALUES ('cash', ?), ('halted', '0')",
                    (str(self.initial_cash),),
                )

    def cash(self) -> float:
        with self._connect() as conn:
            return float(conn.execute("SELECT value FROM meta WHERE key = 'cash'").fetchone()[0])

    def halted(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'halted'").fetchone()
            return bool(row and row[0] == "1")

    def positions(self) -> pd.DataFrame:
        with self._connect() as conn:
            rows = list(conn.execute("SELECT symbol, quantity, avg_price FROM positions"))
        if not rows:
            return pd.DataFrame(columns=["quantity", "avg_price"])
        frame = pd.DataFrame(rows, columns=["symbol", "quantity", "avg_price"]).set_index("symbol")
        return frame

    def mark(self, last_prices: pd.Series) -> float:
        pos = self.positions()
        mv = 0.0
        for symbol, row in pos.iterrows():
            px = float(last_prices.get(symbol, row["avg_price"]))
            mv += float(row["quantity"]) * px
        return self.cash() + mv

    def snapshot(self, last_prices: pd.Series) -> PaperSnapshot:
        return PaperSnapshot(
            cash=self.cash(),
            equity=self.mark(last_prices),
            positions=self.positions(),
            halted=self.halted(),
        )

    def step(
        self,
        strategy: Strategy,
        close: pd.DataFrame,
        *,
        last_bar: pd.Timestamp | None = None,
        commission: float = 0.001,
        slippage: float = 0.0005,
        risk: dict | None = None,
    ) -> PaperSnapshot:
        if close.empty:
            raise ValueError("No price history for paper step")
        ts = last_bar or close.index[-1]
        last_prices = close.loc[ts]
        prev_equity = self.mark(last_prices)

        weights = strategy.generate(close.loc[:ts])
        target = weights.iloc[-1].fillna(0.0)
        if risk:
            target = apply_risk(pd.DataFrame([target]), **risk).iloc[0]

        if self.halted():
            self._record_equity(ts, prev_equity, "halted")
            return self.snapshot(last_prices)

        equity = self.mark(last_prices)
        daily_ret = 0.0 if prev_equity == 0 else (equity / prev_equity - 1.0)
        # Daily loss uses last stored equity if present.
        last_eq = self._last_equity()
        if last_eq is not None and last_eq > 0:
            daily_ret = equity / last_eq - 1.0
        max_daily_loss = float((risk or {}).get("max_daily_loss", 1.0))
        if halt_if_daily_loss(pd.Series([daily_ret]), max_daily_loss).iloc[0]:
            self._set_halted(True)
            self._record_equity(ts, equity, "daily-loss-halt")
            return self.snapshot(last_prices)

        self._rebalance(target, last_prices, equity, commission, slippage)
        marked = self.mark(last_prices)
        self._record_equity(ts, marked, "ok")
        return self.snapshot(last_prices)

    def _rebalance(
        self,
        target: pd.Series,
        last_prices: pd.Series,
        equity: float,
        commission: float,
        slippage: float,
    ) -> None:
        pos = self.positions()
        cash = self.cash()
        symbols = set(target.index) | set(pos.index)
        for symbol in sorted(symbols):
            px = float(last_prices.get(symbol, float("nan")))
            if not pd.notna(px) or px <= 0:
                continue
            desired_value = float(target.get(symbol, 0.0)) * equity
            current_qty = float(pos.loc[symbol, "quantity"]) if symbol in pos.index else 0.0
            current_value = current_qty * px
            delta_value = desired_value - current_value
            if abs(delta_value) < 1.0:
                continue
            qty = delta_value / px
            side = "buy" if qty > 0 else "sell"
            traded = abs(qty)
            slip_px = px * (1.0 + slippage if side == "buy" else 1.0 - slippage)
            notional = traded * slip_px
            fee = notional * commission
            if side == "buy":
                cash -= notional + fee
                new_qty = current_qty + traded
                avg = (
                    (current_qty * float(pos.loc[symbol, "avg_price"]) + traded * slip_px) / new_qty
                    if symbol in pos.index and current_qty
                    else slip_px
                )
            else:
                cash += notional - fee
                new_qty = current_qty - traded
                avg = float(pos.loc[symbol, "avg_price"]) if symbol in pos.index else slip_px
            self._upsert_position(symbol, new_qty, avg)
            self._insert_fill(symbol, side, traded, slip_px, fee)
        self._set_cash(cash)

    def _upsert_position(self, symbol: str, qty: float, avg: float) -> None:
        with self._connect() as conn:
            if abs(qty) < 1e-8:
                conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
                return
            conn.execute(
                """
                INSERT INTO positions(symbol, quantity, avg_price) VALUES (?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET quantity = excluded.quantity, avg_price = excluded.avg_price
                """,
                (symbol, qty, avg),
            )

    def _insert_fill(self, symbol: str, side: str, qty: float, price: float, commission: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO fills(ts, symbol, side, quantity, price, commission) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), symbol, side, qty, price, commission),
            )

    def _set_cash(self, cash: float) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE meta SET value = ? WHERE key = 'cash'", (str(cash),))

    def _set_halted(self, halted: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO meta(key, value) VALUES ('halted', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("1" if halted else "0",),
            )

    def _record_equity(self, ts, equity: float, note: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO equity(ts, cash, equity, note) VALUES (?, ?, ?, ?)",
                (str(ts), self.cash(), equity, note),
            )

    def _last_equity(self) -> float | None:
        with self._connect() as conn:
            row = conn.execute("SELECT equity FROM equity ORDER BY ts DESC LIMIT 1").fetchone()
        return float(row[0]) if row else None

    def fills(self) -> pd.DataFrame:
        with self._connect() as conn:
            rows = list(conn.execute("SELECT ts, symbol, side, quantity, price, commission FROM fills ORDER BY id"))
        return pd.DataFrame(rows, columns=["ts", "symbol", "side", "quantity", "price", "commission"])

    def equity_curve(self) -> pd.DataFrame:
        with self._connect() as conn:
            rows = list(conn.execute("SELECT ts, cash, equity, note FROM equity ORDER BY ts"))
        return pd.DataFrame(rows, columns=["ts", "cash", "equity", "note"])

    def dump(self) -> dict:
        return {
            "cash": self.cash(),
            "halted": self.halted(),
            "positions": self.positions().to_dict(orient="index"),
            "fills": json.loads(self.fills().to_json(orient="records")),
        }
