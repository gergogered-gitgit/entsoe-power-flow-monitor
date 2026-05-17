from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import psycopg
from psycopg.rows import dict_row

from entsoe_power_flow.config import get_settings


@dataclass(frozen=True)
class DashboardData:
    zones: pd.DataFrame
    pairs: pd.DataFrame
    assets: pd.DataFrame
    flows: pd.DataFrame
    capacities: pd.DataFrame
    runs: pd.DataFrame
    last_fetch: object | None
    backend_name: str


def load_dashboard_data() -> DashboardData:
    settings = get_settings()
    if settings.database_url:
        return _load_postgres(settings.database_url)
    return _load_duckdb(settings.duckdb_path)


def _load_duckdb(db_path: Path) -> DashboardData:
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        zones = con.sql("select * from zones order by country, zone_name").df()
        pairs = con.sql("select * from border_pairs where active order by label").df()
        assets = con.sql("select * from border_assets order by from_zone, to_zone, asset_name").df()
        flows = con.sql(
            """
            select timestamp_utc, from_zone, to_zone, mw
            from power_flows_hourly
            order by timestamp_utc desc
            limit 10000
            """
        ).df()
        capacities = con.sql(
            """
            select timestamp_utc, from_zone, to_zone, capacity_mw, capacity_type
            from transfer_capacities_hourly
            order by timestamp_utc desc
            limit 10000
            """
        ).df()
        runs = con.sql("select * from ingestion_runs order by started_at desc limit 20").df()
        last_fetch = con.sql("select max(fetched_at) as fetched_at from power_flows_hourly").fetchone()[0]
    finally:
        con.close()

    return DashboardData(zones, pairs, assets, flows, capacities, runs, last_fetch, "DuckDB")


def _load_postgres(database_url: str) -> DashboardData:
    with psycopg.connect(database_url, row_factory=dict_row) as con:
        zones = _postgres_df(con, "select * from zones order by country, zone_name")
        pairs = _postgres_df(con, "select * from border_pairs where active order by label")
        assets = _postgres_df(con, "select * from border_assets order by from_zone, to_zone, asset_name")
        flows = _postgres_df(
            con,
            """
            select timestamp_utc, from_zone, to_zone, mw
            from power_flows_hourly
            order by timestamp_utc desc
            limit 10000
            """,
        )
        capacities = _postgres_df(
            con,
            """
            select timestamp_utc, from_zone, to_zone, capacity_mw, capacity_type
            from transfer_capacities_hourly
            order by timestamp_utc desc
            limit 10000
            """,
        )
        runs = _postgres_df(con, "select * from ingestion_runs order by started_at desc limit 20")
        last_fetch_df = _postgres_df(
            con,
            "select max(fetched_at) as fetched_at from power_flows_hourly",
        )

    last_fetch = None
    if not last_fetch_df.empty:
        last_fetch = last_fetch_df["fetched_at"].iloc[0]

    return DashboardData(zones, pairs, assets, flows, capacities, runs, last_fetch, "Supabase Postgres")


def _postgres_df(con: psycopg.Connection, query: str) -> pd.DataFrame:
    with con.cursor() as cursor:
        cursor.execute(query)
        return pd.DataFrame(cursor.fetchall())
