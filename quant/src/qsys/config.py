from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PathConfig(BaseModel):
    root: Path = Path("./var")
    lake: Path = Path("./var/lake")
    reports: Path = Path("./var/reports")
    paper_db: Path = Path("./var/paper.sqlite")


class UniverseConfig(BaseModel):
    name: str = "demo"
    source: str = "synthetic"
    symbols: list[str] = Field(default_factory=lambda: ["AAA", "BBB", "CCC"])
    start: str = "2018-01-01"
    end: str | None = None
    adjust: str = "qfq"


class DataConfig(BaseModel):
    default_source: str = "synthetic"
    csv_dir: Path = Path("./data/csv")
    ccxt_exchange: str = "binance"
    ccxt_timeframe: str = "1d"


class BacktestConfig(BaseModel):
    initial_cash: float = 100_000.0
    commission: float = 0.001
    slippage: float = 0.0005
    execution: str = "next_open"
    annualization: int = 252


class PaperConfig(BaseModel):
    initial_cash: float = 100_000.0
    commission: float = 0.001
    slippage: float = 0.0005
    fill: str = "close"


class RiskConfig(BaseModel):
    max_gross_exposure: float = 1.0
    max_weight: float = 0.35
    max_daily_loss: float = 0.03
    cash_buffer: float = 0.02


class StrategyConfig(BaseModel):
    name: str = "sma"
    params: dict[str, Any] = Field(default_factory=lambda: {"fast": 20, "slow": 60})


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QSYS_", extra="ignore")

    paths: PathConfig = Field(default_factory=PathConfig)
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    paper: PaperConfig = Field(default_factory=PaperConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)

    def resolve(self, base_dir: Path) -> "AppConfig":
        """Make relative paths absolute against the quant project directory."""
        payload = self.model_dump()
        for key in ("root", "lake", "reports", "paper_db"):
            payload["paths"][key] = _abs(base_dir, payload["paths"][key])
        payload["data"]["csv_dir"] = _abs(base_dir, payload["data"]["csv_dir"])
        return AppConfig.model_validate(payload)


def _abs(base: Path, value: Path | str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "default.yaml"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or default_config_path()
    if not cfg_path.exists():
        return AppConfig().resolve(project_root())
    with cfg_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return AppConfig.model_validate(raw).resolve(cfg_path.parent.parent)
