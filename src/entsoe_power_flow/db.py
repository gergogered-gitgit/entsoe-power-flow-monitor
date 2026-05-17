from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import duckdb

from entsoe_power_flow.config import get_settings, load_zone_config
from entsoe_power_flow.flow_parser import CapacityPoint, FlowPoint


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    settings = get_settings()
    path = db_path or settings.duckdb_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def init_db() -> None:
    con = connect()
    schema_sql = Path("sql/schema.sql").read_text(encoding="utf-8")
    con.execute(schema_sql)

    config = load_zone_config()
    con.executemany(
        """
        insert or replace into zones (zone_code, zone_name, country, lat, lon)
        values (?, ?, ?, ?, ?)
        """,
        [
            (zone["code"], zone["name"], zone["country"], zone["lat"], zone["lon"])
            for zone in config["zones"]
        ],
    )
    con.executemany(
        """
        insert or replace into border_pairs (from_zone, to_zone, label, active)
        values (?, ?, ?, true)
        """,
        [
            (pair["from_zone"], pair["to_zone"], pair["label"])
            for pair in config["border_pairs"]
        ],
    )
    con.executemany(
        """
        insert or replace into border_assets
            (from_zone, to_zone, asset_name, asset_type, nominal_capacity_mw, source_url, notes)
        values (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                asset["from_zone"],
                asset["to_zone"],
                asset["asset_name"],
                asset["asset_type"],
                asset["nominal_capacity_mw"],
                asset.get("source_url"),
                asset.get("notes"),
            )
            for asset in config.get("border_assets", [])
        ],
    )
    con.close()


def start_ingestion_run(con: duckdb.DuckDBPyConnection, dataset: str) -> UUID:
    run_id = uuid4()
    con.execute(
        """
        insert into ingestion_runs (run_id, dataset, started_at, status)
        values (?, ?, ?, ?)
        """,
        [str(run_id), dataset, utc_now_naive(), "running"],
    )
    return run_id


def finish_ingestion_run(
    con: duckdb.DuckDBPyConnection,
    run_id: UUID,
    status: str,
    rows_loaded: int,
    error: str | None = None,
) -> None:
    con.execute(
        """
        update ingestion_runs
        set finished_at = ?, status = ?, rows_loaded = ?, error = ?
        where run_id = ?
        """,
        [utc_now_naive(), status, rows_loaded, error, str(run_id)],
    )


def upsert_power_flows(
    con: duckdb.DuckDBPyConnection,
    from_zone: str,
    to_zone: str,
    points: list[FlowPoint],
    fetched_at: datetime | None = None,
) -> int:
    if not points:
        return 0

    fetched_at = fetched_at or utc_now_naive()
    con.executemany(
        """
        insert or replace into power_flows_hourly
            (timestamp_utc, from_zone, to_zone, mw, source_revision, fetched_at)
        values (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                point.timestamp_utc.replace(tzinfo=None),
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


def upsert_transfer_capacities(
    con: duckdb.DuckDBPyConnection,
    from_zone: str,
    to_zone: str,
    points: list[CapacityPoint],
    capacity_type: str,
    fetched_at: datetime | None = None,
) -> int:
    if not points:
        return 0

    fetched_at = fetched_at or utc_now_naive()
    con.executemany(
        """
        insert or replace into transfer_capacities_hourly
            (timestamp_utc, from_zone, to_zone, capacity_mw, capacity_type, source_revision, fetched_at)
        values (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                point.timestamp_utc.replace(tzinfo=None),
                from_zone,
                to_zone,
                point.capacity_mw,
                capacity_type,
                point.source_revision,
                fetched_at,
            )
            for point in points
        ],
    )
    return len(points)


if __name__ == "__main__":
    init_db()
    print("Initialized DuckDB schema and seed metadata.")
