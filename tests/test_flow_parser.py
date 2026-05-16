from datetime import datetime, timezone

import pytest

from entsoe_power_flow.flow_parser import parse_physical_flows


SAMPLE_FLOW_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:0">
  <TimeSeries>
    <revisionNumber>2</revisionNumber>
    <Period>
      <timeInterval>
        <start>2026-05-15T00:00Z</start>
        <end>2026-05-15T03:00Z</end>
      </timeInterval>
      <resolution>PT60M</resolution>
      <Point>
        <position>1</position>
        <quantity>1200</quantity>
      </Point>
      <Point>
        <position>2</position>
        <quantity>950.5</quantity>
      </Point>
      <Point>
        <position>3</position>
        <quantity>875</quantity>
      </Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
"""


def test_parse_physical_flows_reads_hourly_points() -> None:
    points = parse_physical_flows(SAMPLE_FLOW_XML)

    assert [point.mw for point in points] == [1200.0, 950.5, 875.0]
    assert points[0].timestamp_utc == datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc)
    assert points[2].timestamp_utc == datetime(2026, 5, 15, 2, 0, tzinfo=timezone.utc)
    assert {point.source_revision for point in points} == {"2"}


def test_parse_physical_flows_rejects_unknown_resolution() -> None:
    xml = SAMPLE_FLOW_XML.replace("<resolution>PT60M</resolution>", "<resolution>P1D</resolution>")

    with pytest.raises(ValueError, match="Unsupported ENTSO-E resolution"):
        parse_physical_flows(xml)
