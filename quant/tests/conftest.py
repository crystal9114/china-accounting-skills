from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from qsys.config import AppConfig


def write_config(root: Path, **overrides) -> Path:
    cfg = AppConfig().model_dump(mode="json")
    cfg["paths"] = {
        "root": str(root),
        "lake": str(root / "lake"),
        "reports": str(root / "reports"),
        "paper_db": str(root / "paper.sqlite"),
    }
    cfg["universe"]["source"] = "synthetic"
    cfg["universe"]["symbols"] = ["AAA", "BBB", "CCC"]
    cfg["universe"]["start"] = "2020-01-01"
    cfg["universe"]["end"] = "2022-12-31"
    cfg["strategy"]["name"] = "equal_weight"
    cfg["strategy"]["params"] = {}
    cfg.update(overrides)
    path = root / "configs" / "default.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def cfg_path(tmp_path: Path) -> Path:
    return write_config(tmp_path)
