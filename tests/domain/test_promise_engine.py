from datetime import date, datetime, time

import pytest

from fulfillment.domain.promise_engine import (
    DeliveryPromiseEngine,
    PromiseRequest,
)


def test_basic_delivery_promise():
    engine = DeliveryPromiseEngine()

    request = PromiseRequest(
        order_id="ORD-PROMISE-001",
        order_ts=datetime(2026, 10, 20, 10, 0),
        service_level="STANDARD",
        destination_zone="ZONE-A",
        processing_days=1,
        transit_days=3,
    )

    result = engine.calculate(request)

    assert result.promised_date == date(2026, 10, 26)
    assert result.total_days == 4
    assert result.cutoff_applied is False


def test_holiday_is_skipped():
    engine = DeliveryPromiseEngine(
        holidays={date(2026, 10, 21)},
    )

    request = PromiseRequest(
        order_id="ORD-PROMISE-002",
        order_ts=datetime(2026, 10, 20, 10, 0),
        service_level="STANDARD",
        destination_zone="ZONE-A",
        processing_days=1,
        transit_days=1,
    )

    result = engine.calculate(request)

    assert result.promised_date == date(2026, 10, 23)
    assert result.holiday_days_skipped == 1


def test_weekend_is_skipped():
    engine = DeliveryPromiseEngine()

    request = PromiseRequest(
        order_id="ORD-PROMISE-003",
        order_ts=datetime(2026, 10, 23, 10, 0),
        service_level="STANDARD",
        destination_zone="ZONE-A",
        processing_days=1,
        transit_days=1,
    )

    result = engine.calculate(request)

    assert result.promised_date == date(2026, 10, 27)
    assert result.non_operating_days_skipped == 2


def test_cutoff_moves_start_to_next_day():
    engine = DeliveryPromiseEngine(
        cutoff_times={"STANDARD": time(17, 0)},
    )

    request = PromiseRequest(
        order_id="ORD-PROMISE-004",
        order_ts=datetime(2026, 10, 20, 18, 0),
        service_level="STANDARD",
        destination_zone="ZONE-A",
        processing_days=1,
        transit_days=1,
    )

    result = engine.calculate(request)

    assert result.cutoff_applied is True
    assert result.promised_date == date(2026, 10, 23)


def test_negative_processing_days_are_rejected():
    engine = DeliveryPromiseEngine()

    request = PromiseRequest(
        order_id="ORD-PROMISE-005",
        order_ts=datetime(2026, 10, 20, 10, 0),
        service_level="STANDARD",
        destination_zone="ZONE-A",
        processing_days=-1,
        transit_days=1,
    )

    with pytest.raises(ValueError):
        engine.calculate(request)


def test_negative_transit_days_are_rejected():
    engine = DeliveryPromiseEngine()

    request = PromiseRequest(
        order_id="ORD-PROMISE-006",
        order_ts=datetime(2026, 10, 20, 10, 0),
        service_level="STANDARD",
        destination_zone="ZONE-A",
        processing_days=1,
        transit_days=-1,
    )

    with pytest.raises(ValueError):
        engine.calculate(request)
