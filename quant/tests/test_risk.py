from __future__ import annotations

import pandas as pd

from qsys.portfolio import apply_risk


def test_max_weight_and_gross_cap():
    weights = pd.DataFrame({"AAA": [1.0], "BBB": [1.0], "CCC": [1.0]})
    out = apply_risk(weights, max_weight=0.5, max_gross_exposure=1.0, cash_buffer=0.1)
    assert (out.abs() <= 0.5 + 1e-12).all().all()
    assert out.abs().sum(axis=1).iloc[0] <= 0.9 + 1e-12
