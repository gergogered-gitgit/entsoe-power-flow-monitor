from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from entsoe_power_flow.config import load_zone_config
from entsoe_power_flow.entsoe_client import EntsoeClient


def backfill_flows() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.days)

    client = EntsoeClient()
    config = load_zone_config()

    for pair in config["border_pairs"]:
        xml = client.fetch_physical_flows(
            pair["from_zone"],
            pair["to_zone"],
            start,
            end,
        )
        print(pair["label"], len(xml))


if __name__ == "__main__":
    backfill_flows()

