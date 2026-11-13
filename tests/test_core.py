from datetime import date
from fulfillment.core import working_day_after
from fulfillment.allocation import Candidate, choose_best


def test_working_day_after_skips_weekend():
    assert working_day_after(date(2026, 10, 30), 1) == date(2026, 11, 2)


def test_allocation_is_deterministic():
    result = choose_best([
        Candidate("FUL-2", 2.0, True),
        Candidate("FUL-1", 1.0, True),
    ])
    assert result.node_id == "FUL-1"


def test_anomaly_ground_truth():
    from pathlib import Path
    from fulfillment.generator import generate
    from fulfillment.validate import validate
    root = Path("data_test")
    generate(root)
    found = set(validate(root))
    assert len(found) == 5
    for name in (
        "PROMISE_BEFORE_ORDER_TIME",
        "ALLOCATION_EXCEEDS_STOCK",
        "UNSUPPORTED_CARRIER_SERVICE_ZONE",
        "SHIPMENT_DELIVERED_BEFORE_DISPATCH",
        "SPLIT_SHIPMENT_STATUS_ROLLUP_ERROR",
    ):
        assert any(issue == name for issue, _ in found)
