"""Streamlit dashboard: 6 panels from config/dashboard.yaml, data from data/logs.jsonl.

Run: streamlit run scripts/dashboard.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config/dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
LOG_PATH = ROOT / "data/logs.jsonl"
PANELS = {p["id"]: p for p in CFG["panels"]}
SYMBOL = {"lte": "≤", "gte": "≥"}

st.set_page_config(page_title=CFG["title"], layout="wide")
st.markdown(
    """<style>
    .card{border:1px solid rgba(128,128,128,.35);border-radius:10px;padding:16px;margin-bottom:12px}
    .card h4{margin:0 0 8px;font-size:15px}
    .card .v{font-size:26px;font-weight:700;color:#4da6ff;line-height:1.3}
    .card .s{opacity:.7;font-size:13px;margin-top:8px}
    </style>""",
    unsafe_allow_html=True,
)


def load() -> pd.DataFrame:
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if LOG_PATH.exists() else []:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=CFG["time_range_minutes"])
    return df[df["ts"] >= cutoff]


def card(panel_id: str, value: str, extra: str = "") -> None:
    p = PANELS[panel_id]
    t = p["threshold"]
    sub = f"{p['unit']} · threshold {t['aggregation']} {SYMBOL[t['operator']]} {t['value']}"
    if extra:
        sub = f"{extra} · {sub}"
    st.markdown(
        f'<div class="card"><h4>{p["title"]}</h4><div class="v">{value}</div><div class="s">{sub}</div></div>',
        unsafe_allow_html=True,
    )


@st.fragment(run_every=CFG["refresh_seconds"])
def render() -> None:
    df = load()
    st.title(CFG["title"])
    left, right = st.columns(2)
    left.caption(f"Source: data/logs.jsonl · last {CFG['time_range_minutes']} minutes")
    right.caption(f"Auto refresh: {CFG['refresh_seconds']}s · records: {len(df)}")
    if df.empty:
        st.warning("Không có log trong time range. Chạy load_test.py.")
        return

    sent = df[df["event"] == "response_sent"]
    recv = df[df["event"] == "request_received"]
    failed = df[df["event"] == "request_failed"]
    q = lambda s, p: s.quantile(p) if len(s) else 0
    per_min = recv.set_index("ts").resample("1min").size()
    err = len(failed) / len(recv) * 100 if len(recv) else 0
    tool = df["tool_success"].dropna().astype(bool) if "tool_success" in df else []
    tool_rate = (sum(tool) / len(tool) * 100) if len(tool) else 100

    c = st.columns(4)
    with c[0]:
        card(
            "latency",
            f"P50 {q(sent['latency_ms'], .5):.0f} · P95 {q(sent['latency_ms'], .95):.0f} · "
            f"P99 {q(sent['latency_ms'], .99):.0f} · TTFT P95 {q(sent['ttft_ms'], .95):.0f}",
        )
    with c[1]:
        card("traffic", f"{len(recv)} requests · {per_min.mean():.2f}/min")
    with c[2]:
        breakdown = failed["error_type"].value_counts().to_dict() if len(failed) else {}
        card("errors", f"Errors {err:.2f}% · Retrieval {tool_rate:.2f}%", f"breakdown: {breakdown}")
    with c[3]:
        card("cost", f"${sent['cost_usd'].sum():.6f}")

    c = st.columns(4)
    with c[0]:
        card("tokens", f"Input {int(sent['tokens_in'].sum())} · Output {int(sent['tokens_out'].sum())}")
    with c[1]:
        card("quality", f"{sent['quality_score'].mean():.3f}")


render()
