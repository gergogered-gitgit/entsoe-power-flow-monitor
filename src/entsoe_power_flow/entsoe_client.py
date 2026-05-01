from __future__ import annotations

from datetime import datetime
from time import sleep

import httpx

from entsoe_power_flow.config import get_settings


class EntsoeClient:
    """Thin ENTSO-E REST client with conservative throttling."""

    def __init__(self, requests_per_second: float = 2.0) -> None:
        self.settings = get_settings()
        self.requests_per_second = requests_per_second

    def get(self, params: dict[str, str]) -> str:
        if not self.settings.entsoe_api_token:
            raise RuntimeError("ENTSOE_API_TOKEN is not set.")

        request_params = dict(params)
        request_params["securityToken"] = self.settings.entsoe_api_token

        sleep(1 / self.requests_per_second)
        response = httpx.get(
            self.settings.entsoe_base_url,
            params=request_params,
            timeout=60,
        )
        response.raise_for_status()
        return response.text

    def fetch_physical_flows(
        self,
        from_zone: str,
        to_zone: str,
        period_start: datetime,
        period_end: datetime,
    ) -> str:
        # Document/process codes are kept explicit so the first API spike can verify them.
        return self.get(
            {
                "documentType": "A11",
                "in_Domain": from_zone,
                "out_Domain": to_zone,
                "periodStart": period_start.strftime("%Y%m%d%H%M"),
                "periodEnd": period_end.strftime("%Y%m%d%H%M"),
            }
        )

