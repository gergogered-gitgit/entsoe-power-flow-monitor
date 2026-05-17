from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from entsoe_power_flow.dashboard_data import load_dashboard_data
from entsoe_power_flow.config import get_settings


st.set_page_config(page_title="ENTSO-E Power Flow Monitor", layout="wide")
st.title("ENTSO-E European Power Flow Monitor")

settings = get_settings()

if not settings.database_url and not settings.duckdb_path.exists():
    st.warning(
        "No data source is configured yet. Set DATABASE_URL for Supabase or run "
        "`python -m entsoe_power_flow.db` for local DuckDB."
    )
    st.stop()

data = load_dashboard_data()
zones = data.zones
pairs = data.pairs
assets = data.assets
flows = data.flows
capacities = data.capacities

zone_names = dict(zip(zones["zone_code"], zones["zone_name"], strict=False))
if not flows.empty:
    flows["from_zone_name"] = flows["from_zone"].map(zone_names)
    flows["to_zone_name"] = flows["to_zone"].map(zone_names)
    flows["border_label"] = flows["from_zone_name"] + " -> " + flows["to_zone_name"]
    latest_by_border = (
        flows.sort_values("timestamp_utc")
        .groupby(["from_zone", "to_zone"], as_index=False, group_keys=False)
        .tail(1)
        .copy()
    )
else:
    latest_by_border = flows.copy()

if not capacities.empty:
    latest_capacities = (
        capacities.sort_values("timestamp_utc")
        .groupby(["from_zone", "to_zone"], as_index=False, group_keys=False)
        .tail(1)
        .copy()
    )
else:
    latest_capacities = capacities.copy()

asset_capacity = (
    assets.groupby(["from_zone", "to_zone"], as_index=False)["nominal_capacity_mw"]
    .sum()
    .rename(columns={"nominal_capacity_mw": "reference_capacity_mw"})
)
if not latest_by_border.empty:
    latest_by_border = latest_by_border.merge(
        latest_capacities[["from_zone", "to_zone", "capacity_mw", "capacity_type"]],
        on=["from_zone", "to_zone"],
        how="left",
    ).merge(asset_capacity, on=["from_zone", "to_zone"], how="left")
    latest_by_border["display_capacity_mw"] = latest_by_border["capacity_mw"].fillna(
        latest_by_border["reference_capacity_mw"]
    )
    latest_by_border["utilization_pct"] = (
        latest_by_border["mw"] / latest_by_border["display_capacity_mw"] * 100
    ).where(latest_by_border["display_capacity_mw"].notna())


def make_flow_map(latest_flows, zones):
    zone_lookup = zones.set_index("zone_code")
    fig = go.Figure()
    max_mw = max(float(latest_flows["mw"].max()), 1.0)

    for flow in latest_flows.itertuples(index=False):
        from_zone = zone_lookup.loc[flow.from_zone]
        to_zone = zone_lookup.loc[flow.to_zone]
        width = 1.5 + (float(flow.mw) / max_mw) * 6
        fig.add_trace(
            go.Scattergeo(
                lon=[from_zone["lon"], to_zone["lon"]],
                lat=[from_zone["lat"], to_zone["lat"]],
                mode="lines",
                line={"width": width, "color": "#2563eb"},
                opacity=0.72,
                text=(
                    f"{from_zone['zone_name']} -> {to_zone['zone_name']}<br>"
                    f"{flow.mw:,.0f} MW<br>{flow.timestamp_utc}"
                    + (
                        f"<br>{flow.utilization_pct:.0f}% of capacity"
                        if hasattr(flow, "utilization_pct") and flow.utilization_pct == flow.utilization_pct
                        else ""
                    )
                ),
                hoverinfo="text",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scattergeo(
            lon=zones["lon"],
            lat=zones["lat"],
            mode="markers+text",
            marker={"size": 9, "color": "#111827", "line": {"width": 1, "color": "white"}},
            text=zones["zone_name"],
            textposition="top center",
            hovertext=zones["zone_name"] + " (" + zones["country"] + ")",
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.update_geos(
        scope="europe",
        projection_type="natural earth",
        showcountries=True,
        countrycolor="#d1d5db",
        showland=True,
        landcolor="#f8fafc",
        showocean=True,
        oceancolor="#e0f2fe",
        lataxis_range=[53, 69],
        lonaxis_range=[10, 32],
    )
    fig.update_layout(
        height=460,
        margin={"l": 0, "r": 0, "t": 16, "b": 0},
    )
    return fig

left, right = st.columns([1, 2])

with left:
    st.caption(f"Data source: {data.backend_name}")
    st.subheader("Coverage")
    st.dataframe(zones, use_container_width=True, hide_index=True)
    st.subheader("Border Pairs")
    st.dataframe(pairs, use_container_width=True, hide_index=True)
    st.subheader("Infrastructure")
    st.dataframe(
        assets[["asset_name", "asset_type", "nominal_capacity_mw"]],
        use_container_width=True,
        hide_index=True,
    )

with right:
    st.subheader("Latest Flows")
    if flows.empty:
        st.info("No flow data loaded yet. Once the ENTSO-E token is available, run a backfill.")
    else:
        latest_timestamp = flows["timestamp_utc"].max()
        total_cross_border_mw = latest_by_border["mw"].sum()

        metric_left, metric_mid, metric_right = st.columns(3)
        metric_left.metric("Latest hour", str(latest_timestamp))
        metric_mid.metric("Latest known flow MW", f"{total_cross_border_mw:,.0f}")
        metric_right.metric("Last fetch", str(data.last_fetch))

        st.subheader("Flow Map")
        st.plotly_chart(make_flow_map(latest_by_border, zones), use_container_width=True)

        selected_pair = st.selectbox(
            "Border pair",
            sorted(flows["border_label"].unique()),
        )
        pair_flows = flows[flows["border_label"] == selected_pair]
        fig = px.line(
            pair_flows.sort_values("timestamp_utc"),
            x="timestamp_utc",
            y="mw",
            title=selected_pair,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Latest Border Snapshot")
        st.dataframe(
            latest_by_border[
                [
                    "border_label",
                    "timestamp_utc",
                    "mw",
                    "display_capacity_mw",
                    "utilization_pct",
                ]
            ].sort_values("utilization_pct", ascending=False, na_position="last"),
            use_container_width=True,
            hide_index=True,
        )

st.subheader("Ingestion Health")
if data.runs.empty:
    st.info("No ingestion runs recorded yet.")
else:
    st.dataframe(data.runs, use_container_width=True, hide_index=True)
