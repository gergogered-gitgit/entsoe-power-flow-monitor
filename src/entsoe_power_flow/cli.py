from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Literal

from entsoe_power_flow.config import load_zone_config
from entsoe_power_flow.config import get_settings
from entsoe_power_flow.entsoe_client import EntsoeClient
from entsoe_power_flow.flow_parser import parse_physical_flows

StorageBackend = Literal["duckdb", "postgres"]


def resolve_storage_backend(requested: str) -> StorageBackend:
    if requested in {"duckdb", "postgres"}:
        return requested
    if get_settings().database_url:
        return "postgres"
    return "duckdb"


def backfill_flows() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--storage",
        choices=["auto", "duckdb", "postgres"],
        default="auto",
        help="Storage backend to write to. Auto uses Postgres when DATABASE_URL is set.",
    )
    args = parser.parse_args()
    storage_backend = resolve_storage_backend(args.storage)

    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.days)

    client = EntsoeClient()
    config = load_zone_config()

    if storage_backend == "postgres":
        from entsoe_power_flow import postgres_db as storage
    else:
        from entsoe_power_flow import db as storage

    storage.init_db()
    con = storage.connect()
    run_id = storage.start_ingestion_run(con, "power_flows_hourly")
    rows_loaded = 0

    try:
        for pair in config["border_pairs"]:
            xml = client.fetch_physical_flows(
                pair["from_zone"],
                pair["to_zone"],
                start,
                end,
            )
            points = parse_physical_flows(xml)
            loaded = storage.upsert_power_flows(con, pair["from_zone"], pair["to_zone"], points)
            rows_loaded += loaded
            print(f"{pair['label']}: loaded {loaded} hourly points")
    except Exception as exc:
        storage.finish_ingestion_run(con, run_id, "failed", rows_loaded, str(exc))
        if hasattr(con, "commit"):
            con.commit()
        con.close()
        raise

    storage.finish_ingestion_run(con, run_id, "succeeded", rows_loaded)
    if hasattr(con, "commit"):
        con.commit()
    con.close()
    print(f"Backfill complete: loaded {rows_loaded} hourly flow rows into {storage_backend}")


if __name__ == "__main__":
    backfill_flows()
