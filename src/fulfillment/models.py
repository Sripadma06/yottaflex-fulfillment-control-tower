from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    zone: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_service_level: Mapped[str] = mapped_column(String(32), nullable=False)
    order_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sku: Mapped[str | None] = mapped_column(String(64))
    quantity: Mapped[int | None] = mapped_column(Integer)
    holiday_affected: Mapped[bool | None] = mapped_column(Boolean)
    delay_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    split_shipment: Mapped[bool | None] = mapped_column(Boolean)

    shipments: Mapped[list["Shipment"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class FulfillmentNode(Base):
    __tablename__ = "fulfillment_nodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[str | None] = mapped_column(String(16))
    daily_capacity_units: Mapped[int | None] = mapped_column(Integer)

    inventory: Mapped[list["Inventory"]] = relationship(
        back_populates="node",
    )


class Carrier(Base):
    __tablename__ = "carriers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    supported_service_levels: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(
        ForeignKey("fulfillment_nodes.id"),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    available_units: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_units: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)

    node: Mapped["FulfillmentNode"] = relationship(
        back_populates="inventory",
    )


class Holiday(Base):
    __tablename__ = "holidays"

    holiday_date: Mapped[date] = mapped_column(Date, primary_key=True)
    holiday_name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    operational_impact: Mapped[str] = mapped_column(String(120), nullable=False)


class AllocationDecision(Base):
    __tablename__ = "allocation_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    candidates: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    node_id: Mapped[str | None] = mapped_column(String(32))
    carrier_id: Mapped[str | None] = mapped_column(String(32))
    inventory_available: Mapped[int | None] = mapped_column(Integer)
    capacity_available: Mapped[int | None] = mapped_column(Integer)
    inventory_constraint: Mapped[bool | None] = mapped_column(Boolean)
    capacity_constraint: Mapped[bool | None] = mapped_column(Boolean)
    carrier_constraint: Mapped[bool | None] = mapped_column(Boolean)


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    dispatch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    shipment_sequence: Mapped[int | None] = mapped_column(Integer)
    node_id: Mapped[str | None] = mapped_column(String(32), index=True)
    carrier_id: Mapped[str | None] = mapped_column(String(32), index=True)
    delay_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    holiday_affected: Mapped[bool | None] = mapped_column(Boolean)
    tracking_event_count: Mapped[int | None] = mapped_column(Integer)

    order: Mapped["Order"] = relationship(
        back_populates="shipments",
    )
    events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment",
        order_by="TrackingEvent.sequence_no",
        cascade="all, delete-orphan",
    )


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(
        ForeignKey("shipments.id"),
        nullable=False,
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    location: Mapped[str] = mapped_column(String(64), nullable=False)

    shipment: Mapped["Shipment"] = relationship(
        back_populates="events",
    )
