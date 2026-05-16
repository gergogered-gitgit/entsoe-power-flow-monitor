from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg import Connection

from entsoe_power_flow.config import get_settings, load_zone_config
from entsoe_power_flow.flow_parser import FlowPoint


def connect(database_url: str | None = None) -> Connection:
    url = database_url or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DATABASE_URL is required for Postgres storage.")
    return psycopg.connect(url)


def utc_now() -> datetime:
    return datetime.now(UTC)


def init_db() -> None:
    with connect() as con:
        schema_sql = Path("sql/supabase_schema.sql").read_text(encoding="utf-8")
        con.execute(schema_sql)

        config = load_zone_config()
        con.executemany(
            """
            insert into zones (zone_code, zone_name, country, lat, lon)
            values (%s, %s, %s, %s, %s)
            on conflict (zone_code) do update set
                zone_name = excluded.zone_name,
                country = excluded.country,
                lat = excluded.lat,
                lon = excluded.lon
            """,
            [
                (zone["code"], zone["name"], zone["country"], zone["lat"], zone["lon"])
                for zone in config["zones"]
            ],
        )
        con.executemany(
            """
            insert into border_pairs (from_zone, to_zone, label, active)
            values (%s, %s, %s, true)
            on conflict (from_zone, to_zone) do update set
                label = excluded.label,
                active = excluded.active
            """,
            [
                (pair["from_zone"], pair["to_zone"], pair["label"])
                for pair in config["border_pairs"]
            ],
        )


def start_ingestion_run(con: Connection, dataset: str) -> UUID:
    run_id = uuid4()
    con.execute(
        """
        insert into ingestion_runs (run_id, dataset, started_at, status)
        values (%s, %s, %s, %s)
        """,
        (run_id, dataset, utc_now(), "running"),
    )
    return run_id


def finish_ingestion_run(
    con: Connection,
    run_id: UUID,
    status: str,
    rows_loaded: int,
    error: str | None = None,
) -> None:
    con.execute(
        """
        update ingestion_runs
        set finished_at = %s, status = %s, rows_loaded = %s, error = %s
        where run_id = %s
        """,
        (utc_now(), status, rows_loaded, error, run_id),
    )


def upsert_power_flows(
    con: Connection,
    from_zone: str,
    to_zone: str,
    points: list[FlowPoint],
    fetched_at: datetime | None = None,
) -> int:
    if not points:
        return 0

    fetched_at = fetched_at or utc_now()
    con.executemany(
        """
        insert into power_flows_hourly
            (timestamp_utc, from_zone, to_zone, mw, source_revision, fetched_at)
        values (%s, %s, %s, %s, %s, %s)
        on conflict (timestamp_utc, from_zone, to_zone) do update set
            mw = excluded.mw,
            source_revision = excluded.source_revision,
            fetched_at = excluded.fetched_at
        """,
        [
            (
                point.timestamp_utc,
                from_zone,
                to_zone,
                point.mw,
                point.source_revision,
                fetched_at,
            )
            for point in points
        ],
    )
    return len(points)
