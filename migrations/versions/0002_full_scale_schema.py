from alembic import op
import sqlalchemy as sa


revision = "0002_full_scale_schema"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # Orders
    op.add_column("orders", sa.Column("sku", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("quantity", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("holiday_affected", sa.Boolean(), nullable=True))
    op.add_column("orders", sa.Column("delay_hours", sa.Numeric(10, 2), nullable=True))
    op.add_column("orders", sa.Column("split_shipment", sa.Boolean(), nullable=True))

    # Fulfillment nodes
    op.add_column("fulfillment_nodes", sa.Column("zone", sa.String(16), nullable=True))
    op.add_column(
        "fulfillment_nodes",
        sa.Column("daily_capacity_units", sa.Integer(), nullable=True),
    )

    # Carriers
    op.create_table(
        "carriers",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("supported_service_levels", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )

    # Inventory
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "node_id",
            sa.String(32),
            sa.ForeignKey("fulfillment_nodes.id"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("available_units", sa.Integer(), nullable=False),
        sa.Column("reserved_units", sa.Integer(), nullable=False),
        sa.Column("capacity_units", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_inventory_node_id",
        "inventory",
        ["node_id"],
    )
    op.create_index(
        "ix_inventory_sku",
        "inventory",
        ["sku"],
    )

    # Holidays
    op.create_table(
        "holidays",
        sa.Column("holiday_date", sa.Date(), primary_key=True),
        sa.Column("holiday_name", sa.String(120), nullable=False),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("operational_impact", sa.String(120), nullable=False),
    )

    # Allocation decisions
    op.add_column(
        "allocation_decisions",
        sa.Column("node_id", sa.String(32), nullable=True),
    )
    op.add_column(
        "allocation_decisions",
        sa.Column("carrier_id", sa.String(32), nullable=True),
    )
    op.add_column(
        "allocation_decisions",
        sa.Column("inventory_available", sa.Integer(), nullable=True),
    )
    op.add_column(
        "allocation_decisions",
        sa.Column("capacity_available", sa.Integer(), nullable=True),
    )
    op.add_column(
        "allocation_decisions",
        sa.Column("inventory_constraint", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "allocation_decisions",
        sa.Column("capacity_constraint", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "allocation_decisions",
        sa.Column("carrier_constraint", sa.Boolean(), nullable=True),
    )

    # Shipments
    op.add_column(
        "shipments",
        sa.Column("shipment_sequence", sa.Integer(), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("node_id", sa.String(32), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("carrier_id", sa.String(32), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("delay_hours", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("holiday_affected", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "shipments",
        sa.Column("tracking_event_count", sa.Integer(), nullable=True),
    )

    # Helpful indexes for the control tower
    op.create_index(
        "ix_orders_order_ts",
        "orders",
        ["order_ts"],
    )
    op.create_index(
        "ix_orders_zone",
        "orders",
        ["zone"],
    )
    op.create_index(
        "ix_orders_sku",
        "orders",
        ["sku"],
    )
    op.create_index(
        "ix_shipments_status",
        "shipments",
        ["status"],
    )
    op.create_index(
        "ix_shipments_node_id",
        "shipments",
        ["node_id"],
    )
    op.create_index(
        "ix_shipments_carrier_id",
        "shipments",
        ["carrier_id"],
    )
    op.create_index(
        "ix_tracking_events_event_time",
        "tracking_events",
        ["event_time"],
    )


def downgrade():
    op.drop_index(
        "ix_tracking_events_event_time",
        table_name="tracking_events",
    )
    op.drop_index(
        "ix_shipments_carrier_id",
        table_name="shipments",
    )
    op.drop_index(
        "ix_shipments_node_id",
        table_name="shipments",
    )
    op.drop_index(
        "ix_shipments_status",
        table_name="shipments",
    )
    op.drop_index(
        "ix_orders_sku",
        table_name="orders",
    )
    op.drop_index(
        "ix_orders_zone",
        table_name="orders",
    )
    op.drop_index(
        "ix_orders_order_ts",
        table_name="orders",
    )

    op.drop_column("shipments", "tracking_event_count")
    op.drop_column("shipments", "holiday_affected")
    op.drop_column("shipments", "delay_hours")
    op.drop_column("shipments", "carrier_id")
    op.drop_column("shipments", "node_id")
    op.drop_column("shipments", "shipment_sequence")

    op.drop_column("allocation_decisions", "carrier_constraint")
    op.drop_column("allocation_decisions", "capacity_constraint")
    op.drop_column("allocation_decisions", "inventory_constraint")
    op.drop_column("allocation_decisions", "capacity_available")
    op.drop_column("allocation_decisions", "inventory_available")
    op.drop_column("allocation_decisions", "carrier_id")
    op.drop_column("allocation_decisions", "node_id")

    op.drop_table("holidays")
    op.drop_index("ix_inventory_sku", table_name="inventory")
    op.drop_index("ix_inventory_node_id", table_name="inventory")
    op.drop_table("inventory")
    op.drop_table("carriers")

    op.drop_column("fulfillment_nodes", "daily_capacity_units")
    op.drop_column("fulfillment_nodes", "zone")

    op.drop_column("orders", "split_shipment")
    op.drop_column("orders", "delay_hours")
    op.drop_column("orders", "holiday_affected")
    op.drop_column("orders", "quantity")
    op.drop_column("orders", "sku")
