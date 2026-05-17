from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree


@dataclass(frozen=True)
class FlowPoint:
    timestamp_utc: datetime
    mw: float
    source_revision: str | None = None


@dataclass(frozen=True)
class CapacityPoint:
    timestamp_utc: datetime
    capacity_mw: float
    source_revision: str | None = None


def parse_physical_flows(xml_text: str) -> list[FlowPoint]:
    """Parse ENTSO-E physical flow XML into hourly points."""
    return [
        FlowPoint(
            timestamp_utc=point.timestamp_utc,
            mw=point.quantity,
            source_revision=point.source_revision,
        )
        for point in _parse_quantity_points(xml_text)
    ]


def parse_transfer_capacities(xml_text: str) -> list[CapacityPoint]:
    """Parse ENTSO-E transfer capacity XML into time-series points."""
    return [
        CapacityPoint(
            timestamp_utc=point.timestamp_utc,
            capacity_mw=point.quantity,
            source_revision=point.source_revision,
        )
        for point in _parse_quantity_points(xml_text)
    ]


@dataclass(frozen=True)
class QuantityPoint:
    timestamp_utc: datetime
    quantity: float
    source_revision: str | None = None


def _parse_quantity_points(xml_text: str) -> list[QuantityPoint]:
    root = ElementTree.fromstring(xml_text)
    namespace = _namespace(root.tag)
    points: list[QuantityPoint] = []

    for time_series in root.findall(f".//{namespace}TimeSeries"):
        revision = _optional_text(time_series, f"{namespace}revisionNumber")
        for period in time_series.findall(f"{namespace}Period"):
            start_text = _required_text(period, f"{namespace}timeInterval/{namespace}start")
            resolution_text = _required_text(period, f"{namespace}resolution")
            period_start = _parse_entsoe_timestamp(start_text)
            step = _parse_resolution(resolution_text)

            for point in period.findall(f"{namespace}Point"):
                position = int(_required_text(point, f"{namespace}position"))
                quantity = float(_required_text(point, f"{namespace}quantity"))
                timestamp = period_start + ((position - 1) * step)
                points.append(
                    QuantityPoint(
                        timestamp_utc=timestamp,
                        quantity=quantity,
                        source_revision=revision,
                    )
                )

    return sorted(points, key=lambda point: point.timestamp_utc)


def _namespace(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", maxsplit=1)[0] + "}"
    return ""


def _optional_text(element: ElementTree.Element, path: str) -> str | None:
    child = element.find(path)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _required_text(element: ElementTree.Element, path: str) -> str:
    value = _optional_text(element, path)
    if not value:
        raise ValueError(f"Missing required ENTSO-E XML value at {path}.")
    return value


def _parse_entsoe_timestamp(value: str) -> datetime:
    timestamp = datetime.strptime(value, "%Y-%m-%dT%H:%MZ")
    return timestamp.replace(tzinfo=timezone.utc)


def _parse_resolution(value: str) -> timedelta:
    if value == "PT60M":
        return timedelta(hours=1)
    if value == "PT30M":
        return timedelta(minutes=30)
    if value == "PT15M":
        return timedelta(minutes=15)
    raise ValueError(f"Unsupported ENTSO-E resolution: {value}")
