from __future__ import annotations

import pandas as pd
import streamlit as st

from qsys.pipeline import make_context, paper_broker, paper_step, pull_data, run_research


st.set_page_config(page_title="qsys", layout="wide")
st.title("qsys — personal quant cockpit")
st.caption("Assembled from open-source libraries. Not a broker. Not investment advice.")

ctx = make_context()
tab_data, tab_bt, tab_paper = st.tabs(["Data", "Backtest", "Paper"])

with tab_data:
    st.subheader("Lake")
    rows = ctx.lake.list_symbols()
    st.dataframe(pd.DataFrame(rows, columns=["source", "symbol"]) if rows else pd.DataFrame())
    if st.button("Pull configured universe"):
        written = pull_data(ctx)
        st.success(f"ingested {written}")
        st.rerun()

with tab_bt:
    st.subheader("Research run")
    if st.button("Run backtest"):
        try:
            result, dest = run_research(ctx)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.json(result.metrics)
            st.line_chart(result.equity.rename("equity"))
            st.caption(f"wrote {dest}")
    latest = ctx.cfg.paths.reports / "latest" / "metrics.csv"
    if latest.exists():
        st.subheader("Latest metrics")
        st.dataframe(pd.read_csv(latest))

with tab_paper:
    st.subheader("Paper ledger")
    broker = paper_broker(ctx)
    st.json({"cash": broker.cash(), "halted": broker.halted()})
    pos = broker.positions()
    if not pos.empty:
        st.dataframe(pos)
    fills = broker.fills()
    if not fills.empty:
        st.dataframe(fills.tail(20))
    if st.button("Paper step (latest bar)"):
        try:
            snap = paper_step(ctx)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.success(f"equity={snap.equity:,.2f}")
            st.rerun()
