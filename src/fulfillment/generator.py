from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import hashlib
import json
import random
from typing import TextIO

from .domain.allocation_engine import (
    AllocationEngine,
    AllocationRequest,
    AllocationResult,
    CarrierRule,
    FulfillmentNode,
)
from .domain.promise_engine import (
    DeliveryPromiseEngine,
    PromiseRequest,
)


UTC = timezone.utc

ZONES = ["Z1", "Z2", "Z3", "Z4", "Z5"]
REGIONS = ["North", "South", "East", "West", "Central"]

SERVICE_LEVELS = {
    "SL-STD": {"hours": 72, "weight": 60},
    "SL-EXP": {"hours": 48, "weight": 30},
    "SL-SAME": {"hours": 24, "weight": 10},
}

ORDER_STATUSES = ["DELIVERED", "SHIPPED", "ALLOCATED", "EXCEPTION"]

CARRIERS = [
    ("CAR-001", "SwiftShip"),
    ("CAR-002", "BlueDart"),
    ("CAR-003", "Delhivery"),
    ("CAR-004", "EcomExpress"),
    ("CAR-005", "XpressBees"),
    ("CAR-006", "DHL"),
    ("CAR-007", "FedEx"),
    ("CAR-008", "Shadowfax"),
    ("CAR-009", "DTDC"),
    ("CAR-010", "Shiprocket"),
]

EVENT_TYPES = [
    "ORDER_CONFIRMED",
    "PICKED_UP",
    "IN_TRANSIT",
    "ARRIVED_AT_HUB",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
]

HOLIDAYS = [
    ("2026-10-02", "Gandhi Jayanti"),
    ("2026-10-20", "Dussehra"),
    ("2026-10-24", "Diwali"),
    ("2026-11-01", "Karnataka Rajyotsava"),
    ("2026-11-14", "Children's Day"),
    ("2026-12-25", "Christmas"),
    ("2027-01-01", "New Year's Day"),
]

BASE_DATE = datetime(2026, 8, 1, tzinfo=UTC)
GENERATION_DAYS = 90


def _write_csv(path: Path, fieldnames: list[str], rows) -> int:
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def _random_order_datetime(rng: random.Random) -> datetime:
    day = rng.randrange(GENERATION_DAYS)
    seconds = rng.randrange(24 * 60 * 60)
    return BASE_DATE + timedelta(days=day, seconds=seconds)


def _weighted_service_level(rng: random.Random) -> str:
    values = list(SERVICE_LEVELS)
    weights = [SERVICE_LEVELS[value]["weight"] for value in values]
    return rng.choices(values, weights=weights, k=1)[0]


def _is_holiday(dt: datetime) -> bool:
    return dt.strftime("%Y-%m-%d") in {date for date, _ in HOLIDAYS}


def _business_delay_hours(start: datetime, hours: int) -> int:
    """
    Add operational hours while introducing additional delay around holidays.
    This is intentionally deterministic from the generated input.
    """
    extra = 0
    cursor = start

    while hours > 0:
        cursor += timedelta(hours=1)

        if cursor.weekday() >= 5:
            extra += 1
        elif _is_holiday(cursor):
            extra += 1

        hours -= 1

    return max(1, int((cursor - start).total_seconds() // 3600) + extra)


def _node_rows():
    for index in range(1, 21):
        zone = ZONES[(index - 1) % len(ZONES)]
        region = REGIONS[(index - 1) % len(REGIONS)]
        yield {
            "node_id": f"NODE-{index:03d}",
            "name": f"Fulfillment Node {index:02d}",
            "region": region,
            "zone": zone,
            "capacity_units": 18000 + ((index * 137) % 12000),
            "daily_capacity_units": 9000 + ((index * 89) % 5000),
        }


def _carrier_rows():
    supported_services = {
        "CAR-001": "SL-STD|SL-EXP|SL-SAME",
        "CAR-002": "SL-STD|SL-EXP",
        "CAR-003": "SL-STD|SL-EXP|SL-SAME",
        "CAR-004": "SL-STD|SL-EXP",
        "CAR-005": "SL-STD|SL-EXP",
        "CAR-006": "SL-EXP|SL-SAME",
        "CAR-007": "SL-EXP|SL-SAME",
        "CAR-008": "SL-STD|SL-SAME",
        "CAR-009": "SL-STD",
        "CAR-010": "SL-STD|SL-EXP",
    }

    for carrier_id, name in CARRIERS:
        yield {
            "carrier_id": carrier_id,
            "carrier_name": name,
            "supported_service_levels": supported_services[carrier_id],
            "active": "true",
        }


def _inventory_rows(rng: random.Random, order_count: int):
    scale_factor = max(order_count / 500, 1.0)

    for node_index in range(1, 21):
        node_id = f"NODE-{node_index:03d}"

        for sku_index in range(1, 11):
            sku = f"SKU-{sku_index:04d}"

            base_capacity = 250 + rng.randrange(750)
            capacity = max(1, int(base_capacity * scale_factor))

            shortage_probability = 0.08
            if rng.random() < shortage_probability:
                available = rng.randrange(
                    0,
                    max(1, capacity // 5),
                )
            else:
                available = rng.randrange(
                    max(1, capacity // 3),
                    capacity + 1,
                )

            yield {
                "node_id": node_id,
                "sku": sku,
                "available_units": available,
                "reserved_units": rng.randrange(
                    0,
                    max(1, available // 4 + 1),
                ),
                "capacity_units": capacity,
            }



def _build_allocation_nodes(
    nodes: list[dict],
    inventory_rows: list[dict],
    carriers: list[dict],
) -> list[FulfillmentNode]:
    inventory_by_node: dict[str, dict[str, int]] = {}

    for row in inventory_rows:
        node_id = row["node_id"]
        inventory_by_node.setdefault(node_id, {})[row["sku"]] = int(
            row["available_units"]
        )

    carrier_rules = []
    for carrier in carriers:
        services = frozenset(
            value
            for value in carrier["supported_service_levels"].split("|")
            if value
        )
        carrier_rules.append(
            CarrierRule(
                carrier_id=carrier["carrier_id"],
                supported_services=services,
                supported_zones=frozenset(ZONES),
                shipping_cost=10.0,
            )
        )

    return [
        FulfillmentNode(
            node_id=node["node_id"],
            supported_zones=frozenset({node["zone"]}),
            inventory_by_sku=inventory_by_node.get(node["node_id"], {}),
            reserved_inventory_by_sku={},
            capacity=int(node["capacity_units"]),
            reserved_capacity=0,
            carrier_rules=tuple(carrier_rules),
            processing_days=1,
            transit_days_by_service={
                "SL-STD": 3,
                "SL-EXP": 2,
                "SL-SAME": 1,
            },
        )
        for node in nodes
    ]


def _holiday_rows():
    for date, name in HOLIDAYS:
        yield {
            "holiday_date": date,
            "holiday_name": name,
            "region": "ALL",
            "operational_impact": "REDUCED_CAPACITY",
        }


def _allocation_candidates(
    rng: random.Random,
    nodes: list[dict],
    carriers: list[dict],
    service_level: str,
    zone: str,
    order_units: int,
):
    candidates = []

    for node in rng.sample(nodes, k=min(5, len(nodes))):
        inventory = rng.randrange(0, 1500)
        capacity = node["capacity_units"]
        distance = rng.randrange(20, 1200)

        inventory_ok = inventory >= order_units
        capacity_ok = capacity >= order_units

        compatible_carriers = [
            carrier
            for carrier in carriers
            if service_level in carrier["supported_service_levels"].split("|")
        ]

        incompatible_carriers = [
            carrier
            for carrier in carriers
            if service_level not in carrier["supported_service_levels"].split("|")
        ]

        if compatible_carriers:
            carrier = rng.choice(compatible_carriers)
        elif incompatible_carriers:
            carrier = rng.choice(incompatible_carriers)
        else:
            carrier = rng.choice(carriers)

        supported = service_level in carrier["supported_service_levels"].split("|")

        score = (
            (35 if inventory_ok else 0)
            + (30 if capacity_ok else 0)
            + (20 if supported else 0)
            + max(0, 15 - distance / 100)
            + (5 if node["zone"] == zone else 0)
        )

        candidates.append(
            {
                "node_id": node["node_id"],
                "carrier_id": carrier["carrier_id"],
                "score": round(score, 2),
                "inventory_available": inventory,
                "capacity_available": capacity,
                "inventory_ok": inventory_ok,
                "capacity_ok": capacity_ok,
                "carrier_service_supported": supported,
                "distance_km": distance,
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates


def _event_rows(
    shipment_id: str,
    dispatch_at: datetime,
    delivered_at: datetime | None,
    location: str,
    anomaly_delivered_before_dispatch: bool = False,
):
    events = [
        ("ORDER_CONFIRMED", dispatch_at - timedelta(hours=4)),
        ("PICKED_UP", dispatch_at),
        ("IN_TRANSIT", dispatch_at + timedelta(hours=8)),
        ("ARRIVED_AT_HUB", dispatch_at + timedelta(hours=18)),
        ("OUT_FOR_DELIVERY", dispatch_at + timedelta(hours=28)),
    ]

    if delivered_at is not None:
        if anomaly_delivered_before_dispatch:
            events.append(("DELIVERED", dispatch_at - timedelta(hours=2)))
        else:
            delivery_event_time = max(
                delivered_at,
                dispatch_at + timedelta(hours=32),
            )
            events.append(("DELIVERED", delivery_event_time))

    for sequence, (event_type, event_time) in enumerate(events, start=1):
        yield {
            "event_id": f"TRK-{shipment_id}-{sequence:03d}",
            "shipment_id": shipment_id,
            "sequence_no": sequence,
            "event_type": event_type,
            "event_time": event_time.isoformat(),
            "location": location,
        }


def generate(
    root: Path,
    seed: int = 20261022,
    scale: str = "starter",
    **kwargs,
) -> dict:
    """
    Generate deterministic fulfillment operational data.

    starter:
        500 orders

    full:
        50,000 orders

    The generator exports operational datasets independently of the
    current relational schema so the data can be inspected, validated,
    loaded, or used for evaluation.
    """
    if scale not in {"starter", "full"}:
        raise ValueError("scale must be 'starter' or 'full'")

    if kwargs:
        unknown = ", ".join(sorted(kwargs))
        raise TypeError(f"unexpected generator arguments: {unknown}")

    order_count = 500 if scale == "starter" else 50_000

    root.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)

    nodes = list(_node_rows())
    carriers = list(_carrier_rows())
    inventory_rows = list(_inventory_rows(rng, order_count))
    allocation_nodes = _build_allocation_nodes(
        nodes,
        inventory_rows,
        carriers,
    )
    allocation_engine = AllocationEngine()
    promise_engine = DeliveryPromiseEngine(
        holidays={
            datetime.fromisoformat(date_text).date()
            for date_text, _ in HOLIDAYS
        },
    )

    # ------------------------------------------------------------------
    # Reference datasets
    # ------------------------------------------------------------------

    nodes_count = _write_csv(
        root / "fulfillment_nodes.csv",
        [
            "node_id",
            "name",
            "region",
            "zone",
            "capacity_units",
            "daily_capacity_units",
        ],
        nodes,
    )

    carriers_count = _write_csv(
        root / "carriers.csv",
        [
            "carrier_id",
            "carrier_name",
            "supported_service_levels",
            "active",
        ],
        carriers,
    )

    inventory_count = _write_csv(
        root / "inventory.csv",
        [
            "node_id",
            "sku",
            "available_units",
            "reserved_units",
            "capacity_units",
        ],
        inventory_rows,
    )

    holidays_count = _write_csv(
        root / "holidays.csv",
        [
            "holiday_date",
            "holiday_name",
            "region",
            "operational_impact",
        ],
        _holiday_rows(),
    )

    # ------------------------------------------------------------------
    # Operational datasets
    # ------------------------------------------------------------------

    orders_path = root / "orders.csv"
    allocations_path = root / "allocations.csv"
    shipments_path = root / "shipments.csv"
    tracking_path = root / "tracking_events.csv"
    ground_truth_path = root / "ground_truth.csv"

    order_fields = [
        "order_id",
        "status",
        "total",
        "zone",
        "service_level",
        "order_ts",
        "promised_date",
        "sku",
        "quantity",
        "holiday_affected",
        "delay_hours",
        "split_shipment",
    ]

    allocation_fields = [
        "allocation_id",
        "order_id",
        "quantity",
        "selected",
        "node_id",
        "carrier_id",
        "score",
        "reason",
        "inventory_available",
        "capacity_available",
        "inventory_constraint",
        "capacity_constraint",
        "carrier_constraint",
        "candidates_json",
        "created_at",
    ]

    shipment_fields = [
        "shipment_id",
        "order_id",
        "shipment_sequence",
        "status",
        "node_id",
        "carrier_id",
        "dispatch_at",
        "delivered_at",
        "delay_hours",
        "holiday_affected",
        "tracking_event_count",
    ]

    tracking_fields = [
        "event_id",
        "shipment_id",
        "sequence_no",
        "event_type",
        "event_time",
        "location",
    ]

    ground_truth_fields = ["issue_type", "entity_id"]

    ground_truth = [
        ("PROMISE_BEFORE_ORDER_TIME", "1"),
        ("ALLOCATION_EXCEEDS_STOCK", "ANOM-ALLOC-0001"),
        ("UNSUPPORTED_CARRIER_SERVICE_ZONE", "SHP-2026-000001"),
        ("SHIPMENT_DELIVERED_BEFORE_DISPATCH", "TRK-SHP-2026-000001-002"),
        ("SPLIT_SHIPMENT_STATUS_ROLLUP_ERROR", "ORD-2026-000001"),
    ]

    split_target = max(1, int(order_count * 0.08))
    delay_target = max(1, int(order_count * 0.10))
    exception_target = max(1, int(order_count * 0.03))

    total_shipments = 0
    total_events = 0
    split_orders = 0
    delayed_shipments = 0
    exception_orders = 0
    allocation_count = 0
    missing_tracking_shipment_id = None

    with (
        orders_path.open("w", newline="", encoding="utf-8") as orders_handle,
        allocations_path.open("w", newline="", encoding="utf-8") as allocations_handle,
        shipments_path.open("w", newline="", encoding="utf-8") as shipments_handle,
        tracking_path.open("w", newline="", encoding="utf-8") as tracking_handle,
    ):
        order_writer = csv.DictWriter(orders_handle, fieldnames=order_fields)
        allocation_writer = csv.DictWriter(
            allocations_handle,
            fieldnames=allocation_fields,
        )
        shipment_writer = csv.DictWriter(
            shipments_handle,
            fieldnames=shipment_fields,
        )
        tracking_writer = csv.DictWriter(
            tracking_handle,
            fieldnames=tracking_fields,
        )

        order_writer.writeheader()
        allocation_writer.writeheader()
        shipment_writer.writeheader()
        tracking_writer.writeheader()

        for index in range(1, order_count + 1):
            order_id = f"ORD-2026-{index:06d}"

            order_ts = _random_order_datetime(rng)
            zone = rng.choice(ZONES)
            service_level = _weighted_service_level(rng)
            sku = f"SKU-{rng.randrange(1, 11):04d}"
            quantity = rng.randrange(1, 8)

            holiday_affected = _is_holiday(order_ts)
            split_shipment = index <= split_target

            if index == 1:
                # First record is intentionally inconsistent so the generated
                # dataset contains a deterministic split-shipment anomaly.
                status = "DELIVERED"
            elif index <= exception_target:
                status = "EXCEPTION"
                exception_orders += 1
            else:
                status_roll = rng.random()
                if status_roll < 0.58:
                    status = "DELIVERED"
                elif status_roll < 0.84:
                    status = "SHIPPED"
                else:
                    status = "ALLOCATED"

            delay_hours = 0
            if index <= delay_target or rng.random() < 0.08:
                delay_hours = rng.randrange(6, 49)
                if holiday_affected:
                    delay_hours += 12
                delayed_shipments += 1

            total = round(rng.uniform(150, 6500), 2)

            allocation_request = AllocationRequest(
                order_id=order_id,
                sku=sku,
                quantity=quantity,
                destination_zone=zone,
                service_level=service_level,
                order_ts=order_ts,
            )

            try:
                allocation_result = allocation_engine.allocate(
                    allocation_request,
                    allocation_nodes,
                    allow_split=split_shipment,
                )
            except RuntimeError as exc:
                message = str(exc)
                if (
                    "Unable to fulfill" not in message
                    and "No feasible fulfillment node" not in message
                ):
                    raise

                allocation_result = AllocationResult(
                    order_id=order_id,
                    allocations=tuple(),
                    split=False,
                    candidates=tuple(),
                    reasoning={
                        "strategy": "exception",
                        "exception": "INSUFFICIENT_INVENTORY",
                        "message": str(exc),
                    },
                )

            if not allocation_result.allocations:
                order_writer.writerow(
                    {
                        "order_id": order_id,
                        "status": "EXCEPTION",
                        "total": f"{total:.2f}",
                        "zone": zone,
                        "service_level": service_level,
                        "order_ts": order_ts.isoformat(),
                        "promised_date": "",
                        "sku": sku,
                        "quantity": quantity,
                        "holiday_affected": str(holiday_affected).lower(),
                        "delay_hours": delay_hours,
                        "split_shipment": "false",
                    }
                )
                exception_orders += 1
                continue

            primary_allocation = allocation_result.allocations[0]
            promise_result = promise_engine.calculate(
                PromiseRequest(
                    order_id=order_id,
                    order_ts=order_ts,
                    service_level=service_level,
                    destination_zone=zone,
                    processing_days=1,
                    transit_days=int(
                        primary_allocation.get("estimated_delivery_days", 0)
                    ),
                )
            )

            if index == 1:
                promise_result = replace(
                    promise_result,
                    promised_date=(order_ts - timedelta(days=1)).date(),
                )

            reserved_nodes = list(allocation_nodes)

            for allocation in allocation_result.allocations:
                allocation_node_id = str(allocation["node_id"])
                allocation_quantity = int(allocation["quantity"])

                node_index = next(
                    (
                        index
                        for index, node in enumerate(reserved_nodes)
                        if node.node_id == allocation_node_id
                    ),
                    None,
                )

                if node_index is None:
                    raise RuntimeError(
                        f"Allocation node {allocation_node_id} "
                        f"was not found for order {order_id}."
                    )

                reserved_nodes[node_index] = reserved_nodes[node_index].reserve(
                    sku,
                    allocation_quantity,
                )

            allocation_nodes[:] = reserved_nodes

            actual_split_shipment = allocation_result.split

            if actual_split_shipment:
                split_orders += 1

            order_writer.writerow(
                {
                    "order_id": order_id,
                    "status": status,
                    "total": f"{total:.2f}",
                    "zone": zone,
                    "service_level": service_level,
                    "order_ts": order_ts.isoformat(),
                    "promised_date": promise_result.promised_date.isoformat(),
                    "sku": sku,
                    "quantity": quantity,
                    "holiday_affected": str(holiday_affected).lower(),
                    "delay_hours": delay_hours,
                    "split_shipment": str(actual_split_shipment).lower(),
                }
            )

            selected_allocation = allocation_result.allocations[0]
            selected_node_id = str(selected_allocation["node_id"])
            selected_carrier_id = str(selected_allocation["carrier_id"])

            candidate_rows = []
            for candidate in allocation_result.candidates:
                candidate_rows.append(
                    {
                        "node_id": candidate.node_id,
                        "carrier_id": candidate.carrier_id or "",
                        "score": round(candidate.score, 2),
                        "inventory_available": candidate.atp,
                        "capacity_available": candidate.capacity_available,
                        "inventory_ok": candidate.atp >= quantity,
                        "capacity_ok": candidate.capacity_available >= quantity,
                        "carrier_service_supported": candidate.carrier_id is not None,
                        "distance_km": 0,
                        "feasible": candidate.feasible,
                        "reasons": list(candidate.reasons),
                    }
                )

            candidates = candidate_rows

            selected = next(
                candidate
                for candidate in candidates
                if candidate["node_id"] == selected_node_id
                and candidate["carrier_id"] == selected_carrier_id
            )

            inventory_constraint = selected["inventory_available"] < quantity
            capacity_constraint = selected["capacity_available"] < quantity
            carrier_constraint = not selected["carrier_service_supported"]

            reason = json.dumps(
                allocation_result.reasoning,
                sort_keys=True,
            )

            allocations = allocation_result.allocations

            for allocation_sequence, allocation in enumerate(allocations, start=1):
                allocation_id = (
                    "ANOM-ALLOC-0001"
                    if index == 1 and allocation_sequence == 1
                    else f"ALLOC-{index:06d}-{allocation_sequence:02d}"
                )

                allocation_node_id = str(allocation["node_id"])
                allocation_carrier_id = str(allocation["carrier_id"])
                allocation_quantity = int(allocation.get("quantity", quantity))

                allocation_candidate = next(
                    (
                        candidate
                        for candidate in candidates
                        if candidate["node_id"] == allocation_node_id
                        and candidate["carrier_id"] == allocation_carrier_id
                    ),
                    None,
                )

                if allocation_candidate is None:
                    raise RuntimeError(
                        f"Allocation candidate missing for "
                        f"{order_id}: {allocation_node_id}/{allocation_carrier_id}"
                    )

                allocation_reasoning = dict(allocation_result.reasoning)
                allocation_reasoning["allocation_sequence"] = allocation_sequence
                allocation_reasoning["allocation_quantity"] = allocation_quantity
                allocation_reasoning["split"] = allocation_result.split

                allocation_writer.writerow(
                    {
                        "allocation_id": allocation_id,
                        "order_id": order_id,
                        "quantity": allocation_quantity,
                        "selected": "true",
                        "node_id": allocation_node_id,
                        "carrier_id": allocation_carrier_id,
                        "score": f"{allocation_candidate['score']:.2f}",
                        "reason": json.dumps(
                            allocation_reasoning,
                            sort_keys=True,
                        ),
                        "inventory_available": allocation_candidate["inventory_available"],
                        "capacity_available": allocation_candidate["capacity_available"],
                        "inventory_constraint": str(
                            allocation_candidate["inventory_available"]
                            < allocation_quantity
                        ).lower(),
                        "capacity_constraint": str(
                            allocation_candidate["capacity_available"]
                            < allocation_quantity
                        ).lower(),
                        "carrier_constraint": str(
                            not allocation_candidate["carrier_service_supported"]
                        ).lower(),
                        "candidates_json": _json_candidates(candidates),
                        "created_at": (
                            order_ts + timedelta(minutes=5)
                        ).isoformat(),
                    }
                )

            allocation_count += 1

            shipment_count_for_order = 2 if actual_split_shipment else 1

            for shipment_sequence in range(1, shipment_count_for_order + 1):
                shipment_id = (
                    "SHP-2026-000001"
                    if index == 1 and shipment_sequence == 1
                    else f"SHP-2026-{total_shipments + 1:06d}"
                )

                node = (
                    nodes[(index + shipment_sequence) % len(nodes)]
                    if split_shipment
                    else nodes[index % len(nodes)]
                )

                carrier = carriers[
                    (index + shipment_sequence) % len(carriers)
                ]

                dispatch_at = order_ts + timedelta(
                    hours=rng.randrange(8, 30)
                )

                shipment_delay = delay_hours
                if split_shipment and shipment_sequence == 2:
                    shipment_delay += rng.randrange(4, 18)

                if holiday_affected:
                    shipment_delay += 8

                delivered_at = None

                if status == "DELIVERED":
                    delivered_at = dispatch_at + timedelta(
                        hours=_business_delay_hours(
                            dispatch_at,
                            SERVICE_LEVELS[service_level]["hours"]
                            // 2
                            + shipment_delay,
                        )
                    )

                # First generated shipment is the legacy anomaly shipment.
                anomaly_early_delivery = index == 1 and shipment_sequence == 1

                if anomaly_early_delivery:
                    delivered_at = dispatch_at - timedelta(hours=2)

                if index == 1:
                    carrier = carriers[0]

                shipment_status = status

                if shipment_sequence == 1 and index == 1:
                    shipment_status = "DELIVERED"

                # Deliberately keep the second split shipment open so the
                # order-level delivered status conflicts with shipment state.
                if index == 1 and shipment_sequence == 2:
                    shipment_status = "SHIPPED"
                    delivered_at = None

                if status == "ALLOCATED":
                    shipment_status = "ALLOCATED"
                    delivered_at = None
                elif status == "SHIPPED":
                    shipment_status = "SHIPPED"
                    delivered_at = None
                elif status == "EXCEPTION":
                    shipment_status = "EXCEPTION"
                    delivered_at = None

                shipment_event_rows = list(
                    _event_rows(
                        shipment_id,
                        dispatch_at,
                        delivered_at,
                        node["region"],
                        anomaly_delivered_before_dispatch=anomaly_early_delivery,
                    )
                )

                # Keep one shipment intentionally without tracking so the
                # anomaly detector has a real missing-tracking scenario.
                missing_tracking = (
                    index == exception_target
                    and shipment_sequence == 1
                )

                if missing_tracking:
                    shipment_event_rows = []
                    missing_tracking_shipment_id = shipment_id

                for event in shipment_event_rows:
                    tracking_writer.writerow(event)
                    total_events += 1

                shipment_writer.writerow(
                    {
                        "shipment_id": shipment_id,
                        "order_id": order_id,
                        "shipment_sequence": shipment_sequence,
                        "status": shipment_status,
                        "node_id": node["node_id"],
                        "carrier_id": carrier["carrier_id"],
                        "dispatch_at": dispatch_at.isoformat(),
                        "delivered_at": (
                            delivered_at.isoformat()
                            if delivered_at is not None
                            else ""
                        ),
                        "delay_hours": shipment_delay,
                        "holiday_affected": str(holiday_affected).lower(),
                        "tracking_event_count": len(shipment_event_rows),
                    }
                )

                total_shipments += 1

    # Ensure the full dataset comfortably exceeds the requested threshold.
    # Every normal shipment has at least five events, so 50k orders already
    # produce well over 100k events.
    if scale == "full" and total_events < 100_000:
        raise RuntimeError(
            f"Generated only {total_events} tracking events; "
            "expected at least 100000."
        )

    _write_csv(
        ground_truth_path,
        ground_truth_fields,
        (
            {"issue_type": issue_type, "entity_id": entity_id}
            for issue_type, entity_id in ground_truth
        ),
    )

    summary = {
        "status": "generated",
        "root": str(root),
        "scale": scale,
        "seed": seed,
        "orders": order_count,
        "fulfillment_nodes": nodes_count,
        "carriers": carriers_count,
        "inventory_records": inventory_count,
        "holidays": holidays_count,
        "allocation_decisions": allocation_count,
        "shipments": total_shipments,
        "split_orders": split_orders,
        "split_shipment_pct": round(
            split_orders / order_count * 100,
            2,
        ),
        "delayed_shipments": delayed_shipments,
        "exception_orders": exception_orders,
        "tracking_events": total_events,
        "ground_truth": len(ground_truth),
        "exports": [
            "orders.csv",
            "fulfillment_nodes.csv",
            "carriers.csv",
            "inventory.csv",
            "holidays.csv",
            "allocations.csv",
            "shipments.csv",
            "tracking_events.csv",
            "ground_truth.csv",
        ],
    }

    _write_generation_artifacts(
        root,
        seed=seed,
        scale=scale,
        summary=summary,
    )

    return summary



def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_generation_artifacts(
    root: Path,
    *,
    seed: int,
    scale: str,
    summary: dict,
) -> None:
    files = sorted(
        path
        for path in root.iterdir()
        if path.is_file()
        and path.name not in {"checksums.sha256", "manifest.json"}
    )

    checksums_path = root / "checksums.sha256"

    with checksums_path.open("w", encoding="utf-8", newline="") as handle:
        for file_path in files:
            handle.write(
                f"{_sha256_file(file_path)}  {file_path.name}\n"
            )

    manifest = {
        "generator": {
            "name": "fulfillment-optimizer",
            "version": "1.1.0",
        },
        "dataset": {
            "scale": scale,
            "seed": seed,
            "deterministic": True,
        },
        "summary": summary,
        "files": [
            {
                "name": file_path.name,
                "size_bytes": file_path.stat().st_size,
                "sha256": _sha256_file(file_path),
            }
            for file_path in files
        ],
        "checksums_file": checksums_path.name,
    }

    with (root / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def _json_candidates(candidates: list[dict]) -> str:
    import json

    return json.dumps(candidates, separators=(",", ":"))
