from datetime import datetime, timezone
from pathlib import Path

from entsoe_power_flow.db import connect, upsert_power_flows, upsert_transfer_capacities
from entsoe_power_flow.flow_parser import CapacityPoint, FlowPoint


def test_upsert_power_flows_replaces_existing_rows(tmp_path) -> None:
    db_path = tmp_path / "entsoe.duckdb"
    con = connect(db_path)
    schema_sql = (Path(__file__).parents[1] / "sql" / "schema.sql").read_text(encoding="utf-8")
    con.execute(schema_sql)

    timestamp = datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc)
    first = [FlowPoint(timestamp_utc=timestamp, mw=100.0, source_revision="1")]
    second = [FlowPoint(timestamp_utc=timestamp, mw=125.0, source_revision="2")]

    assert upsert_power_flows(con, "from", "to", first) == 1
    assert upsert_power_flows(con, "from", "to", second) == 1

    rows = con.sql("select mw, source_revision from power_flows_hourly").fetchall()
    assert rows == [(125.0, "2")]
    con.close()


def test_upsert_transfer_capacities_replaces_existing_rows(tmp_path) -> None:
    db_path = tmp_path / "entsoe.duckdb"
    con = connect(db_path)
    schema_sql = (Path(__file__).parents[1] / "sql" / "schema.sql").read_text(encoding="utf-8")
    con.execute(schema_sql)

    timestamp = datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc)
    first = [CapacityPoint(timestamp_utc=timestamp, capacity_mw=900.0, source_revision="1")]
    second = [CapacityPoint(timestamp_utc=timestamp, capacity_mw=950.0, source_revision="2")]

    assert upsert_transfer_capacities(con, "from", "to", first, "estimated_day_ahead") == 1
    assert upsert_transfer_capacities(con, "from", "to", second, "estimated_day_ahead") == 1

    rows = con.sql(
        "select capacity_mw, capacity_type, source_revision from transfer_capacities_hourly"
    ).fetchall()
    assert rows == [(950.0, "estimated_day_ahead", "2")]
    con.close()
