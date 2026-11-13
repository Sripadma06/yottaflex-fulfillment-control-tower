import csv
import io
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .db import engine


def _read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def _copy_rows(
    connection: Connection,
    table: str,
    column_map: list[tuple[str, str]],
    rows,
) -> int:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")

    count = 0

    for row in rows:
        values = []

        for db_column, csv_column in column_map:
            value = row.get(csv_column)

            if value is None or value == "":
                values.append(r"\N")
            elif db_column == "candidates":
                values.append(
                    json.dumps(
                        json.loads(value),
                        separators=(",", ":"),
                    )
                )
            else:
                values.append(value)

        writer.writerow(values)
        count += 1

    buffer.seek(0)

    raw_connection = connection.connection.driver_connection
    raw_cursor = raw_connection.cursor()

    try:
        with raw_cursor.copy(
            f"COPY {table} ({', '.join(db for db, _ in column_map)}) "
            "FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
        ) as copy:
            copy.write(buffer.getvalue())
    finally:
        raw_cursor.close()

    return count


def load(root: str | Path = "data/output") -> dict:
    root = Path(root)

    required = [
        "orders.csv",
        "fulfillment_nodes.csv",
        "carriers.csv",
        "inventory.csv",
        "holidays.csv",
        "allocations.csv",
        "shipments.csv",
        "tracking_events.csv",
    ]

    missing = [
        name for name in required
        if not (root / name).exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing generated files: " + ", ".join(missing)
        )

    counts = {}

    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE "
                "tracking_events, shipments, allocation_decisions, "
                "inventory, holidays, carriers, orders, "
                "fulfillment_nodes "
                "RESTART IDENTITY CASCADE"
            )
        )

        counts["fulfillment_nodes"] = _copy_rows(
            connection,
            "fulfillment_nodes",
            [
                ("id", "node_id"),
                ("name", "name"),
                ("region", "region"),
                ("zone", "zone"),
                ("capacity_units", "capacity_units"),
                ("daily_capacity_units", "daily_capacity_units"),
            ],
            _read_csv(root / "fulfillment_nodes.csv"),
        )

        counts["carriers"] = _copy_rows(
            connection,
            "carriers",
            [
                ("id", "carrier_id"),
                ("name", "carrier_name"),
                ("supported_service_levels", "supported_service_levels"),
                ("active", "active"),
            ],
            _read_csv(root / "carriers.csv"),
        )

        counts["holidays"] = _copy_rows(
            connection,
            "holidays",
            [
                ("holiday_date", "holiday_date"),
                ("holiday_name", "holiday_name"),
                ("region", "region"),
                ("operational_impact", "operational_impact"),
            ],
            _read_csv(root / "holidays.csv"),
        )

        counts["orders"] = _copy_rows(
            connection,
            "orders",
            [
                ("id", "order_id"),
                ("status", "status"),
                ("total", "total"),
                ("zone", "zone"),
                ("requested_service_level", "service_level"),
                ("order_ts", "order_ts"),
                ("sku", "sku"),
                ("quantity", "quantity"),
                ("holiday_affected", "holiday_affected"),
                ("delay_hours", "delay_hours"),
                ("split_shipment", "split_shipment"),
            ],
            _read_csv(root / "orders.csv"),
        )

        counts["inventory"] = _copy_rows(
            connection,
            "inventory",
            [
                ("node_id", "node_id"),
                ("sku", "sku"),
                ("available_units", "available_units"),
                ("reserved_units", "reserved_units"),
                ("capacity_units", "capacity_units"),
            ],
            _read_csv(root / "inventory.csv"),
        )

        counts["allocation_decisions"] = _copy_rows(
            connection,
            "allocation_decisions",
            [
                ("order_id", "order_id"),
                ("selected", "selected"),
                ("node_id", "node_id"),
                ("carrier_id", "carrier_id"),
                ("score", "score"),
                ("reason", "reason"),
                ("inventory_available", "inventory_available"),
                ("capacity_available", "capacity_available"),
                ("inventory_constraint", "inventory_constraint"),
                ("capacity_constraint", "capacity_constraint"),
                ("carrier_constraint", "carrier_constraint"),
                ("candidates", "candidates_json"),
                ("created_at", "created_at"),
            ],
            _read_csv(root / "allocations.csv"),
        )

        counts["shipments"] = _copy_rows(
            connection,
            "shipments",
            [
                ("id", "shipment_id"),
                ("order_id", "order_id"),
                ("shipment_sequence", "shipment_sequence"),
                ("status", "status"),
                ("node_id", "node_id"),
                ("carrier_id", "carrier_id"),
                ("dispatch_at", "dispatch_at"),
                ("delivered_at", "delivered_at"),
                ("delay_hours", "delay_hours"),
                ("holiday_affected", "holiday_affected"),
                ("tracking_event_count", "tracking_event_count"),
            ],
            _read_csv(root / "shipments.csv"),
        )

        counts["tracking_events"] = _copy_rows(
            connection,
            "tracking_events",
            [
                ("id", "event_id"),
                ("shipment_id", "shipment_id"),
                ("sequence_no", "sequence_no"),
                ("event_type", "event_type"),
                ("event_time", "event_time"),
                ("location", "location"),
            ],
            _read_csv(root / "tracking_events.csv"),
        )

        for table in [
            "fulfillment_nodes",
            "carriers",
            "holidays",
            "orders",
            "inventory",
            "allocation_decisions",
            "shipments",
            "tracking_events",
        ]:
            connection.execute(text(f"ANALYZE {table}"))

    return {
        "status": "loaded",
        "root": str(root),
        "counts": counts,
        "total_rows": sum(counts.values()),
    }

    buffer.seek(0)

    raw_connection = connection.connection.driver_connection
    raw_cursor = raw_connection.cursor()

    try:
        with raw_cursor.copy(
            f"COPY {table} ({', '.join(db for db, _ in column_map)}) "
            "FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
        ) as copy:
            copy.write(buffer.getvalue())
    finally:
        raw_cursor.close()

    return count


def load(root: str | Path = "data/output") -> dict:
    root = Path(root)

    required = [
        "orders.csv",
        "fulfillment_nodes.csv",
        "carriers.csv",
        "inventory.csv",
        "holidays.csv",
        "allocations.csv",
        "shipments.csv",
        "tracking_events.csv",
    ]

    missing = [
        name
        for name in required
        if not (root / name).exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing generated files: " + ", ".join(missing)
        )

    counts = {}

    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE "
                "tracking_events, shipments, allocation_decisions, "
                "inventory, holidays, carriers, orders, "
                "fulfillment_nodes "
                "RESTART IDENTITY CASCADE"
            )
        )

        counts["fulfillment_nodes"] = _copy_rows(
            connection,
            "fulfillment_nodes",
            [
                ("id", "node_id"),
                ("name", "name"),
                ("region", "region"),
                ("zone", "zone"),
                ("capacity_units", "capacity_units"),
                ("daily_capacity_units", "daily_capacity_units"),
            ],
            _read_csv(root / "fulfillment_nodes.csv"),
        )

        counts["carriers"] = _copy_rows(
            connection,
            "carriers",
            [
                ("id", "carrier_id"),
                ("name", "carrier_name"),
                ("supported_service_levels", "supported_service_levels"),
                ("active", "active"),
            ],
            _read_csv(root / "carriers.csv"),
        )

        counts["holidays"] = _copy_rows(
            connection,
            "holidays",
            [
                ("holiday_date", "holiday_date"),
                ("holiday_name", "holiday_name"),
                ("region", "region"),
                ("operational_impact", "operational_impact"),
            ],
            _read_csv(root / "holidays.csv"),
        )

        counts["orders"] = _copy_rows(
            connection,
            "orders",
            [
                ("id", "order_id"),
                ("status", "status"),
                ("total", "total"),
                ("zone", "zone"),
                ("requested_service_level", "service_level"),
                ("order_ts", "order_ts"),
                ("sku", "sku"),
                ("quantity", "quantity"),
                ("holiday_affected", "holiday_affected"),
                ("delay_hours", "delay_hours"),
                ("split_shipment", "split_shipment"),
            ],
            _read_csv(root / "orders.csv"),
        )

        counts["inventory"] = _copy_rows(
            connection,
            "inventory",
            [
                ("node_id", "node_id"),
                ("sku", "sku"),
                ("available_units", "available_units"),
                ("reserved_units", "reserved_units"),
                ("capacity_units", "capacity_units"),
            ],
            _read_csv(root / "inventory.csv"),
        )

        counts["allocation_decisions"] = _copy_rows(
            connection,
            "allocation_decisions",
            [
                ("order_id", "order_id"),
                ("selected", "selected"),
                ("node_id", "node_id"),
                ("carrier_id", "carrier_id"),
                ("score", "score"),
                ("reason", "reason"),
                ("inventory_available", "inventory_available"),
                ("capacity_available", "capacity_available"),
                ("inventory_constraint", "inventory_constraint"),
                ("capacity_constraint", "capacity_constraint"),
                ("carrier_constraint", "carrier_constraint"),
                ("candidates", "candidates_json"),
                ("created_at", "created_at"),
            ],
            _read_csv(root / "allocations.csv"),
        )

        counts["shipments"] = _copy_rows(
            connection,
            "shipments",
            [
                ("id", "shipment_id"),
                ("order_id", "order_id"),
                ("shipment_sequence", "shipment_sequence"),
                ("status", "status"),
                ("node_id", "node_id"),
                ("carrier_id", "carrier_id"),
                ("dispatch_at", "dispatch_at"),
                ("delivered_at", "delivered_at"),
                ("delay_hours", "delay_hours"),
                ("holiday_affected", "holiday_affected"),
                ("tracking_event_count", "tracking_event_count"),
            ],
            _read_csv(root / "shipments.csv"),
        )

        counts["tracking_events"] = _copy_rows(
            connection,
            "tracking_events",
            [
                ("id", "event_id"),
                ("shipment_id", "shipment_id"),
                ("sequence_no", "sequence_no"),
                ("event_type", "event_type"),
                ("event_time", "event_time"),
                ("location", "location"),
            ],
            _read_csv(root / "tracking_events.csv"),
        )

        for table in [
            "fulfillment_nodes",
            "carriers",
            "holidays",
            "orders",
            "inventory",
            "allocation_decisions",
            "shipments",
            "tracking_events",
        ]:
            connection.execute(text(f"ANALYZE {table}"))

    return {
        "status": "loaded",
        "root": str(root),
        "counts": counts,
        "total_rows": sum(counts.values()),
    }
