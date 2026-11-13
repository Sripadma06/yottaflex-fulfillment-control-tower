from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "orders",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("zone", sa.String(16), nullable=False),
        sa.Column("requested_service_level", sa.String(32), nullable=False),
        sa.Column("order_ts", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_table(
        "fulfillment_nodes",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("capacity_units", sa.Integer(), nullable=False),
    )
    op.create_table(
        "allocation_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.String(32), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Numeric(12, 4)),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_allocation_decisions_order_id", "allocation_decisions", ["order_id"])
    op.create_table(
        "shipments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("order_id", sa.String(32), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("dispatch_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"])
    op.create_table(
        "tracking_events",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("shipment_id", sa.String(32), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(64), nullable=False),
    )
    op.create_index("ix_tracking_events_shipment_id", "tracking_events", ["shipment_id"])


def downgrade():
    op.drop_index("ix_tracking_events_shipment_id", table_name="tracking_events")
    op.drop_table("tracking_events")
    op.drop_index("ix_shipments_order_id", table_name="shipments")
    op.drop_table("shipments")
    op.drop_index("ix_allocation_decisions_order_id", table_name="allocation_decisions")
    op.drop_table("allocation_decisions")
    op.drop_table("fulfillment_nodes")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_table("orders")
