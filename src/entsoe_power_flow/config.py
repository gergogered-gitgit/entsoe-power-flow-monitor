from __future__ import annotations

from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    entsoe_api_token: str | None = Field(default=None, alias="ENTSOE_API_TOKEN")
    entsoe_base_url: str = Field(
        default="https://web-api.tp.entsoe.eu/api", alias="ENTSOE_BASE_URL"
    )
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    duckdb_path: Path = Path("data/processed/entsoe.duckdb")


def get_settings() -> Settings:
    load_dotenv()
    return Settings()


def load_zone_config(path: Path = Path("config/zones.yaml")) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)

