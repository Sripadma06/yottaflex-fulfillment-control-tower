from datetime import datetime, time

from fulfillment.domain.allocation_engine import (
    AllocationEngine,
    AllocationRequest,
    CarrierRule,
    FulfillmentNode,
)


def make_request(quantity: int = 10) -> AllocationRequest:
    return AllocationRequest(
        order_id="ORD-TEST-ENGINE-001",
        sku="SKU-001",
        quantity=quantity,
        destination_zone="ZONE-A",
        service_level="STANDARD",
        order_ts=datetime(2026, 10, 20, 10, 0),
    )


def make_node(
    node_id: str,
    inventory: int,
    capacity: int = 100,
    reserved_inventory: int = 0,
    reserved_capacity: int = 0,
    zones: frozenset[str] = frozenset({"ZONE-A"}),
    services: frozenset[str] = frozenset({"STANDARD"}),
) -> FulfillmentNode:
    return FulfillmentNode(
        node_id=node_id,
        supported_zones=zones,
        inventory_by_sku={"SKU-001": inventory},
        reserved_inventory_by_sku={"SKU-001": reserved_inventory},
        capacity=capacity,
        reserved_capacity=reserved_capacity,
        carrier_rules=(
            CarrierRule(
                carrier_id="CARRIER-1",
                supported_services=services,
                supported_zones=frozenset({"ZONE-A"}),
                shipping_cost=10.0,
            ),
        ),
        cutoff_times={"STANDARD": time(17, 0)},
        processing_days=1,
        transit_days_by_service={"STANDARD": 3},
    )


def test_atp_excludes_reserved_inventory():
    node = make_node(
        "NODE-1",
        inventory=100,
        reserved_inventory=95,
    )

    assert node.available_to_promise("SKU-001") == 5


def test_ineligible_node_is_excluded_when_inventory_is_insufficient():
    engine = AllocationEngine()

    request = make_request(quantity=20)

    node = make_node(
        "NODE-1",
        inventory=10,
    )

    result = engine.rank_candidates(request, [node])

    assert result[0].feasible is False
    assert "INSUFFICIENT_INVENTORY" in result[0].reasons


def test_destination_zone_is_validated():
    engine = AllocationEngine()

    request = make_request()

    node = make_node(
        "NODE-1",
        inventory=100,
        zones=frozenset({"ZONE-B"}),
    )

    result = engine.rank_candidates(request, [node])

    assert result[0].feasible is False
    assert "UNSUPPORTED_DESTINATION_ZONE" in result[0].reasons


def test_carrier_service_is_validated():
    engine = AllocationEngine()

    request = make_request()

    node = make_node(
        "NODE-1",
        inventory=100,
        services=frozenset({"EXPRESS"}),
    )

    result = engine.rank_candidates(request, [node])

    assert result[0].feasible is False
    assert "NO_CARRIER_SERVICE" in result[0].reasons


def test_cutoff_is_validated():
    engine = AllocationEngine()

    request = AllocationRequest(
        order_id="ORD-TEST-ENGINE-002",
        sku="SKU-001",
        quantity=10,
        destination_zone="ZONE-A",
        service_level="STANDARD",
        order_ts=datetime(2026, 10, 20, 18, 0),
    )

    node = make_node(
        "NODE-1",
        inventory=100,
    )

    result = engine.rank_candidates(request, [node])

    assert result[0].feasible is False
    assert "CARRIER_CUTOFF_PASSED" in result[0].reasons


def test_best_feasible_node_is_selected():
    engine = AllocationEngine()

    request = make_request()

    expensive = FulfillmentNode(
        node_id="NODE-EXPENSIVE",
        supported_zones=frozenset({"ZONE-A"}),
        inventory_by_sku={"SKU-001": 100},
        capacity=100,
        carrier_rules=(
            CarrierRule(
                carrier_id="CARRIER-EXPENSIVE",
                supported_services=frozenset({"STANDARD"}),
                supported_zones=frozenset({"ZONE-A"}),
                shipping_cost=90.0,
            ),
        ),
        cutoff_times={"STANDARD": time(17, 0)},
        processing_days=1,
        transit_days_by_service={"STANDARD": 3},
    )

    cheap = make_node(
        "NODE-CHEAP",
        inventory=100,
    )

    result = engine.allocate(
        request,
        [expensive, cheap],
        allow_split=False,
    )

    assert result.split is False
    assert result.allocations[0]["node_id"] == "NODE-CHEAP"
    assert result.allocations[0]["quantity"] == 10


def test_split_fulfillment_uses_multiple_nodes():
    engine = AllocationEngine()

    request = make_request(quantity=30)

    node_one = make_node(
        "NODE-1",
        inventory=15,
    )

    node_two = make_node(
        "NODE-2",
        inventory=15,
    )

    result = engine.allocate(
        request,
        [node_one, node_two],
        allow_split=True,
    )

    assert result.split is True
    assert len(result.allocations) == 2
    assert sum(
        int(item["quantity"])
        for item in result.allocations
    ) == 30


def test_reserve_reduces_available_inventory_and_capacity():
    node = make_node(
        "NODE-RESERVE",
        inventory=100,
        capacity=100,
    )

    reserved = node.reserve("SKU-001", 25)

    assert reserved.available_to_promise("SKU-001") == 75
    assert reserved.remaining_capacity() == 75
    assert reserved.reserved_inventory_by_sku["SKU-001"] == 25
    assert reserved.reserved_capacity == 25
    assert node.available_to_promise("SKU-001") == 100
    assert node.remaining_capacity() == 100


def test_reserve_rejects_inventory_over_allocation():
    node = make_node(
        "NODE-RESERVE",
        inventory=20,
        capacity=100,
    )

    try:
        node.reserve("SKU-001", 21)
    except ValueError as exc:
        assert "Insufficient ATP" in str(exc)
    else:
        raise AssertionError("Expected inventory reservation to fail.")


def test_reserve_rejects_capacity_over_allocation():
    node = make_node(
        "NODE-RESERVE",
        inventory=100,
        capacity=20,
    )

    try:
        node.reserve("SKU-001", 21)
    except ValueError as exc:
        assert "Insufficient capacity" in str(exc)
    else:
        raise AssertionError("Expected capacity reservation to fail.")
