from __future__ import annotations

from pathlib import Path

import duckdb

from entsoe_power_flow.config import get_settings, load_zone_config


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    settings = get_settings()
    path = db_path or settings.duckdb_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


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
    con.close()


if __name__ == "__main__":
    init_db()
    print("Initialized DuckDB schema and seed metadata.")

