from __future__ import annotations

import duckdb
import plotly.express as px
import streamlit as st

from entsoe_power_flow.config import get_settings


st.set_page_config(page_title="ENTSO-E Power Flow Monitor", layout="wide")
st.title("ENTSO-E European Power Flow Monitor")

settings = get_settings()

if not settings.duckdb_path.exists():
    st.warning("Local database has not been initialized yet. Run `python -m entsoe_power_flow.db`.")
    st.stop()

con = duckdb.connect(str(settings.duckdb_path), read_only=True)

zones = con.sql("select * from zones order by country, zone_name").df()
pairs = con.sql("select * from border_pairs where active order by label").df()
flows = con.sql(
    """
    select timestamp_utc, from_zone, to_zone, mw
    from power_flows_hourly
    order by timestamp_utc desc
    limit 10000
    """
).df()

left, right = st.columns([1, 2])

with left:
    st.subheader("Coverage")
    st.dataframe(zones, use_container_width=True, hide_index=True)
    st.subheader("Border Pairs")
    st.dataframe(pairs, use_container_width=True, hide_index=True)

with right:
    st.subheader("Latest Flows")
    if flows.empty:
        st.info("No flow data loaded yet. Once the ENTSO-E token is available, run a backfill.")
    else:
        selected_pair = st.selectbox(
            "Border pair",
            sorted((flows["from_zone"] + " -> " + flows["to_zone"]).unique()),
        )
        from_zone, to_zone = selected_pair.split(" -> ")
        pair_flows = flows[(flows["from_zone"] == from_zone) & (flows["to_zone"] == to_zone)]
        fig = px.line(
            pair_flows.sort_values("timestamp_utc"),
            x="timestamp_utc",
            y="mw",
            title=selected_pair,
        )
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Ingestion Health")
try:
    runs = con.sql("select * from ingestion_runs order by started_at desc limit 20").df()
    st.dataframe(runs, use_container_width=True, hide_index=True)
except duckdb.CatalogException:
    st.info("No ingestion runs recorded yet.")
