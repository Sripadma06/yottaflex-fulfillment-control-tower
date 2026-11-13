from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def detect_anomalies(root: Path) -> list[dict]:
    orders = _read_csv(root / "orders.csv")
    allocations = _read_csv(root / "allocations.csv")
    shipments = _read_csv(root / "shipments.csv")
    tracking_events = _read_csv(root / "tracking_events.csv")
    nodes = _read_csv(root / "fulfillment_nodes.csv")
    carriers = _read_csv(root / "carriers.csv")
    inventory = _read_csv(root / "inventory.csv")

    anomalies: list[dict] = []

    def add(issue_type: str, entity_id: str, severity: str, message: str) -> None:
        anomalies.append({
            "issue_type": issue_type,
            "entity_id": entity_id,
            "severity": severity,
            "message": message,
        })

    orders_by_id = {r["order_id"]: r for r in orders}
    nodes_by_id = {r["node_id"]: r for r in nodes}
    carriers_by_id = {r["carrier_id"]: r for r in carriers}

    shipments_by_order: dict[str, list[dict[str, str]]] = {}
    for shipment in shipments:
        shipments_by_order.setdefault(shipment["order_id"], []).append(shipment)

    events_by_shipment: dict[str, list[dict[str, str]]] = {}
    for event in tracking_events:
        events_by_shipment.setdefault(event["shipment_id"], []).append(event)

    for order in orders:
        order_ts = _parse_datetime(order.get("order_ts"))
        promised_date = order.get("promised_date")

        if not order_ts or not promised_date:
            continue

        promised_date_value = datetime.fromisoformat(promised_date).date()

        if promised_date_value < order_ts.date():
            add(
                "PROMISE_BEFORE_ORDER_TIME",
                order["order_id"],
                "CRITICAL",
                f"Order {order['order_id']} has promised date {promised_date} before order time {order_ts.isoformat()}.",
            )

    for allocation in allocations:
        if allocation.get("inventory_constraint", "").lower() != "true":
            continue

        order = orders_by_id.get(allocation["order_id"])
        if not order:
            continue

        quantity = int(order.get("quantity") or 0)
        available = int(float(allocation.get("inventory_available") or 0))

        if available < quantity:
            add(
                "ALLOCATION_EXCEEDS_STOCK",
                allocation["allocation_id"],
                "CRITICAL",
                f"Order {allocation['order_id']} requires {quantity} units but selected node {allocation['node_id']} has only {available} available.",
            )

    for allocation in allocations:
        # Only the selected allocation represents the operational decision.
        # Candidate alternatives are evaluated by the allocation engine but
        # should not be reported as production anomalies.
        if str(allocation.get("selected", "")).lower() != "true":
            continue

        order = orders_by_id.get(allocation["order_id"])
        carrier = carriers_by_id.get(allocation["carrier_id"])

        if not order or not carrier:
            continue

        supported = carrier["supported_service_levels"].split("|")

        if order["service_level"] not in supported:
            add(
                "UNSUPPORTED_CARRIER_SERVICE_ZONE",
                allocation["allocation_id"],
                "HIGH",
                f"Carrier {allocation['carrier_id']} does not support {order['service_level']} for order {order['order_id']}.",
            )

    for shipment in shipments:
        dispatch_at = _parse_datetime(shipment.get("dispatch_at"))
        delivered_at = _parse_datetime(shipment.get("delivered_at"))

        if dispatch_at and delivered_at and delivered_at < dispatch_at:
            add(
                "SHIPMENT_DELIVERED_BEFORE_DISPATCH",
                shipment["shipment_id"],
                "CRITICAL",
                f"Shipment delivered at {delivered_at.isoformat()} before dispatch at {dispatch_at.isoformat()}.",
            )

        for event in events_by_shipment.get(shipment["shipment_id"], []):
            if event.get("event_type") != "DELIVERED":
                continue

            event_time = _parse_datetime(event.get("event_time"))

            if dispatch_at and event_time and event_time < dispatch_at:
                add(
                    "SHIPMENT_DELIVERED_BEFORE_DISPATCH",
                    event["event_id"],
                    "CRITICAL",
                    f"Tracking event reports delivery at {event_time.isoformat()} before dispatch at {dispatch_at.isoformat()}.",
                )

    for shipment in shipments:
        if not events_by_shipment.get(shipment["shipment_id"]):
            add(
                "MISSING_TRACKING_EVENTS",
                shipment["shipment_id"],
                "MEDIUM",
                f"Shipment {shipment['shipment_id']} has no tracking events.",
            )

    for order_id, order in orders_by_id.items():
        if order.get("split_shipment", "").lower() != "true":
            continue

        order_shipments = shipments_by_order.get(order_id, [])

        if len(order_shipments) < 2:
            add(
                "SPLIT_SHIPMENT_STATUS_ROLLUP_ERROR",
                order_id,
                "HIGH",
                f"Order {order_id} is marked as split shipment but has only {len(order_shipments)} shipment(s).",
            )
            continue

        statuses = {shipment["status"] for shipment in order_shipments}

        if order["status"] == "DELIVERED" and statuses != {"DELIVERED"}:
            add(
                "SPLIT_SHIPMENT_STATUS_ROLLUP_ERROR",
                order_id,
                "HIGH",
                f"Order is DELIVERED but split shipment statuses are {sorted(statuses)}.",
            )

    for allocation in allocations:
        if allocation.get("capacity_constraint", "").lower() != "true":
            continue

        order = orders_by_id.get(allocation["order_id"])
        if not order or allocation["node_id"] not in nodes_by_id:
            continue

        quantity = int(order.get("quantity") or 0)
        capacity = int(float(allocation.get("capacity_available") or 0))

        if capacity < quantity:
            add(
                "ALLOCATION_EXCEEDS_CAPACITY",
                allocation["allocation_id"],
                "HIGH",
                f"Order requires {quantity} units but node {allocation['node_id']} has capacity {capacity}.",
            )

    for order in orders:
        pass

    for shipment in shipments:
        if shipment["order_id"] not in orders_by_id:
            add(
                "ORPHAN_SHIPMENT",
                shipment["shipment_id"],
                "HIGH",
                f"Shipment references missing order {shipment['order_id']}.",
            )

        if shipment["node_id"] not in nodes_by_id:
            add(
                "UNKNOWN_FULFILLMENT_NODE",
                shipment["shipment_id"],
                "HIGH",
                f"Shipment references unknown node {shipment['node_id']}.",
            )

        if shipment["carrier_id"] not in carriers_by_id:
            add(
                "UNKNOWN_CARRIER",
                shipment["shipment_id"],
                "HIGH",
                f"Shipment references unknown carrier {shipment['carrier_id']}.",
            )

    for row in inventory:
        available = int(float(row.get("available_units") or 0))
        capacity = int(float(row.get("capacity_units") or 0))

        if available > capacity:
            add(
                "INVENTORY_EXCEEDS_CAPACITY",
                f"{row['node_id']}:{row['sku']}",
                "HIGH",
                f"Inventory availability {available} exceeds declared capacity {capacity}.",
            )

    unique: dict[tuple[str, str], dict] = {}

    for anomaly in anomalies:
        key = (anomaly["issue_type"], anomaly["entity_id"])
        unique.setdefault(key, anomaly)

    return list(unique.values())


def anomaly_summary(root: Path) -> dict:
    anomalies = detect_anomalies(root)

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for anomaly in anomalies:
        issue_type = anomaly["issue_type"]
        severity = anomaly["severity"]

        by_type[issue_type] = by_type.get(issue_type, 0) + 1
        by_severity[severity] = by_severity.get(severity, 0) + 1

    return {
        "total": len(anomalies),
        "by_type": dict(sorted(by_type.items())),
        "by_severity": dict(sorted(by_severity.items())),
        "anomalies": anomalies,
    }
