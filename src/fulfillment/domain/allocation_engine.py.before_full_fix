from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, time
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CarrierRule:
    carrier_id: str
    supported_services: frozenset[str]
    supported_zones: frozenset[str]
    shipping_cost: float = 0.0


@dataclass(frozen=True)
class FulfillmentNode:
    node_id: str
    supported_zones: frozenset[str]
    inventory_by_sku: Mapping[str, int]
    reserved_inventory_by_sku: Mapping[str, int] = field(default_factory=dict)
    capacity: int = 0
    reserved_capacity: int = 0
    carrier_rules: Sequence[CarrierRule] = field(default_factory=tuple)
    cutoff_times: Mapping[str, time] = field(default_factory=dict)
    operating_weekdays: frozenset[int] = frozenset(range(7))
    processing_days: int = 1
    transit_days_by_service: Mapping[str, int] = field(default_factory=dict)
    distance_km: float = 0.0

    def available_to_promise(self, sku: str) -> int:
        inventory = int(self.inventory_by_sku.get(sku, 0))
        reserved = int(self.reserved_inventory_by_sku.get(sku, 0))
        return max(inventory - reserved, 0)

    def remaining_capacity(self) -> int:
        return max(self.capacity - self.reserved_capacity, 0)

    def reserve(self, sku: str, quantity: int) -> "FulfillmentNode":
        if quantity <= 0:
            raise ValueError("Reservation quantity must be greater than zero.")

        if self.available_to_promise(sku) < quantity:
            raise ValueError(
                f"Insufficient ATP for {self.node_id}/{sku}: "
                f"requested={quantity}, available={self.available_to_promise(sku)}."
            )

        if self.remaining_capacity() < quantity:
            raise ValueError(
                f"Insufficient capacity for {self.node_id}: "
                f"requested={quantity}, available={self.remaining_capacity()}."
            )

        reserved_inventory = dict(self.reserved_inventory_by_sku)
        reserved_inventory[sku] = (
            int(reserved_inventory.get(sku, 0)) + quantity
        )

        return replace(
            self,
            reserved_inventory_by_sku=reserved_inventory,
            reserved_capacity=self.reserved_capacity + quantity,
        )


@dataclass(frozen=True)
class AllocationRequest:
    order_id: str
    sku: str
    quantity: int
    destination_zone: str
    service_level: str
    order_ts: datetime


@dataclass(frozen=True)
class CandidateEvaluation:
    node_id: str
    feasible: bool
    atp: int
    capacity_available: int
    carrier_id: str | None
    estimated_delivery_days: int | None
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AllocationResult:
    order_id: str
    allocations: tuple[dict[str, object], ...]
    split: bool
    candidates: tuple[CandidateEvaluation, ...]
    reasoning: dict[str, object]


class AllocationEngine:
    """
    Deterministic fulfillment allocation engine.

    Evaluation order:
    inventory -> capacity -> destination zone -> carrier/service
    -> operating calendar/cutoff -> delivery feasibility -> scoring.
    """

    DEFAULT_WEIGHTS = {
        "lateness_risk": 0.35,
        "shipping_cost": 0.20,
        "node_utilization": 0.15,
        "split_count": 0.15,
        "inventory_risk": 0.15,
    }

    def __init__(
        self,
        weights: Mapping[str, float] | None = None,
    ) -> None:
        configured = dict(self.DEFAULT_WEIGHTS)
        if weights:
            configured.update(
                {
                    key: float(value)
                    for key, value in weights.items()
                    if key in configured
                }
            )

        total = sum(max(value, 0.0) for value in configured.values())

        if total <= 0:
            raise ValueError("Allocation weights must contain a positive total.")

        self.weights = {
            key: max(value, 0.0) / total
            for key, value in configured.items()
        }

    def evaluate_node(
        self,
        request: AllocationRequest,
        node: FulfillmentNode,
    ) -> CandidateEvaluation:
        reasons: list[str] = []

        atp = node.available_to_promise(request.sku)
        capacity = node.remaining_capacity()

        inventory_ok = atp >= request.quantity
        capacity_ok = capacity >= request.quantity

        zone_ok = (
            request.destination_zone in node.supported_zones
        )

        carrier = self._find_carrier(node, request)

        carrier_ok = carrier is not None

        schedule_ok = self._within_operating_schedule(
            request,
            node,
        )

        cutoff_ok = self._within_cutoff(
            request,
            node,
        )

        if not inventory_ok:
            reasons.append("INSUFFICIENT_INVENTORY")

        if not capacity_ok:
            reasons.append("WAREHOUSE_CAPACITY_EXCEEDED")

        if not zone_ok:
            reasons.append("UNSUPPORTED_DESTINATION_ZONE")

        if not carrier_ok:
            reasons.append("NO_CARRIER_SERVICE")

        if not schedule_ok:
            reasons.append("NODE_NOT_OPERATING")

        if not cutoff_ok:
            reasons.append("CARRIER_CUTOFF_PASSED")

        feasible = not reasons

        delivery_days: int | None = None
        shipping_cost = 0.0

        if carrier is not None:
            delivery_days = (
                node.processing_days
                + int(
                    node.transit_days_by_service.get(
                        request.service_level,
                        0,
                    )
                )
            )
            shipping_cost = carrier.shipping_cost

        score = (
            self._score(
                request=request,
                node=node,
                atp=atp,
                delivery_days=delivery_days,
                shipping_cost=shipping_cost,
            )
            if feasible
            else float("inf")
        )

        return CandidateEvaluation(
            node_id=node.node_id,
            feasible=feasible,
            atp=atp,
            capacity_available=capacity,
            carrier_id=carrier.carrier_id if carrier else None,
            estimated_delivery_days=delivery_days,
            score=score,
            reasons=tuple(reasons),
        )

    def rank_candidates(
        self,
        request: AllocationRequest,
        nodes: Sequence[FulfillmentNode],
    ) -> list[CandidateEvaluation]:
        evaluated = [
            self.evaluate_node(request, node)
            for node in nodes
        ]

        return sorted(
            evaluated,
            key=lambda candidate: (
                not candidate.feasible,
                candidate.score,
                candidate.node_id,
            ),
        )

    def allocate(
        self,
        request: AllocationRequest,
        nodes: Sequence[FulfillmentNode],
        allow_split: bool = True,
    ) -> AllocationResult:
        if request.quantity <= 0:
            raise ValueError("Order quantity must be greater than zero.")

        if not nodes:
            raise ValueError("At least one fulfillment node is required.")

        candidates = self.rank_candidates(request, nodes)

        best = next(
            (
                candidate
                for candidate in candidates
                if candidate.feasible
            ),
            None,
        )

        if allow_split:
            split_result = self._allocate_split(
                request,
                nodes,
                candidates,
            )

            if split_result.split:
                return split_result

        if best is not None:
            allocation = self._build_allocation(
                request,
                best,
            )

            return AllocationResult(
                order_id=request.order_id,
                allocations=(allocation,),
                split=False,
                candidates=tuple(candidates),
                reasoning={
                    "strategy": "single_node",
                    "selected_node": best.node_id,
                    "candidate_count": len(candidates),
                    "feasible_candidate_count": sum(
                        candidate.feasible
                        for candidate in candidates
                    ),
                    "weights": dict(self.weights),
                },
            )

        if allow_split:
            return self._allocate_split(
                request,
                nodes,
                candidates,
            )

        raise RuntimeError(
            f"No feasible fulfillment node for {request.order_id}."
        )

    def _find_carrier(
        self,
        node: FulfillmentNode,
        request: AllocationRequest,
    ) -> CarrierRule | None:
        compatible = [
            carrier
            for carrier in node.carrier_rules
            if request.service_level in carrier.supported_services
            and request.destination_zone in carrier.supported_zones
        ]

        if not compatible:
            return None

        return min(
            compatible,
            key=lambda carrier: (
                carrier.shipping_cost,
                carrier.carrier_id,
            ),
        )

    def _within_operating_schedule(
        self,
        request: AllocationRequest,
        node: FulfillmentNode,
    ) -> bool:
        return request.order_ts.weekday() in node.operating_weekdays

    def _within_cutoff(
        self,
        request: AllocationRequest,
        node: FulfillmentNode,
    ) -> bool:
        cutoff = node.cutoff_times.get(request.service_level)

        if cutoff is None:
            return True

        return request.order_ts.time() <= cutoff

    def _score(
        self,
        request: AllocationRequest,
        node: FulfillmentNode,
        atp: int,
        delivery_days: int | None,
        shipping_cost: float,
    ) -> float:
        delivery = float(delivery_days or 0)

        lateness_risk = min(
            max(delivery - self._target_days(request.service_level), 0)
            / max(self._target_days(request.service_level), 1),
            1.0,
        )

        utilization = (
            node.reserved_capacity / node.capacity
            if node.capacity > 0
            else 1.0
        )

        inventory_risk = 1.0 - min(
            atp / max(request.quantity * 2, 1),
            1.0,
        )

        cost_risk = min(
            max(shipping_cost, 0.0) / 100.0,
            1.0,
        )

        return (
            self.weights["lateness_risk"] * lateness_risk
            + self.weights["shipping_cost"] * cost_risk
            + self.weights["node_utilization"] * utilization
            + self.weights["split_count"] * 0.0
            + self.weights["inventory_risk"] * inventory_risk
        )

    @staticmethod
    def _target_days(service_level: str) -> int:
        service = service_level.upper()

        if service == "EXPRESS":
            return 2

        if service == "STANDARD":
            return 5

        return 7

    @staticmethod
    def _build_allocation(
        request: AllocationRequest,
        candidate: CandidateEvaluation,
    ) -> dict[str, object]:
        return {
            "node_id": candidate.node_id,
            "quantity": request.quantity,
            "carrier_id": candidate.carrier_id,
            "service_level": request.service_level,
            "estimated_delivery_days": (
                candidate.estimated_delivery_days
            ),
            "score": candidate.score,
            "reasoning": {
                "inventory_atp": candidate.atp,
                "capacity_available": candidate.capacity_available,
                "carrier_id": candidate.carrier_id,
                "delivery_days": candidate.estimated_delivery_days,
                "score": candidate.score,
                "feasible": candidate.feasible,
            },
        }

    def _allocate_split(
        self,
        request: AllocationRequest,
        nodes: Sequence[FulfillmentNode],
        candidates: Sequence[CandidateEvaluation],
    ) -> AllocationResult:
        remaining = request.quantity
        allocations: list[dict[str, object]] = []

        eligible = [
            candidate
            for candidate in candidates
            if candidate.capacity_available > 0
            and candidate.atp > 0
            and candidate.carrier_id is not None
            and "UNSUPPORTED_DESTINATION_ZONE" not in candidate.reasons
            and "NO_CARRIER_SERVICE" not in candidate.reasons
            and "NODE_NOT_OPERATING" not in candidate.reasons
            and "CARRIER_CUTOFF_PASSED" not in candidate.reasons
        ]

        if len(eligible) >= 2 and request.quantity >= 2:
            first = eligible[0]
            second = eligible[1]

            first_quantity = max(
                1,
                min(
                    first.atp,
                    request.quantity // 2,
                ),
            )

            second_quantity = min(
                second.atp,
                request.quantity - first_quantity,
            )

            if second_quantity > 0:
                first_allocation = self._build_allocation(
                    request,
                    first,
                )
                first_allocation["quantity"] = first_quantity
                first_allocation["reasoning"] = {
                    **first_allocation["reasoning"],
                    "split": True,
                    "remaining_before": request.quantity,
                }

                allocations.append(first_allocation)
                remaining -= first_quantity

                second_allocation = self._build_allocation(
                    request,
                    second,
                )
                second_allocation["quantity"] = second_quantity
                second_allocation["reasoning"] = {
                    **second_allocation["reasoning"],
                    "split": True,
                    "remaining_before": remaining,
                }

                allocations.append(second_allocation)
                remaining -= second_quantity

        for candidate in eligible:
            if remaining <= 0:
                break

            if any(
                allocation["node_id"] == candidate.node_id
                for allocation in allocations
            ):
                continue

            quantity = min(
                remaining,
                candidate.atp,
            )

            if quantity <= 0:
                continue

            allocation = self._build_allocation(
                request,
                candidate,
            )
            allocation["quantity"] = quantity
            allocation["reasoning"] = {
                **allocation["reasoning"],
                "split": True,
                "remaining_before": remaining,
            }

            allocations.append(allocation)
            remaining -= quantity

        if remaining > 0:
            raise RuntimeError(
                f"Unable to fulfill {request.order_id}; "
                f"{remaining} units remain unallocated."
            )

        return AllocationResult(
            order_id=request.order_id,
            allocations=tuple(allocations),
            split=len(allocations) > 1,
            candidates=tuple(candidates),
            reasoning={
                "strategy": "split_fulfillment",
                "split_count": max(len(allocations) - 1, 0),
                "selected_nodes": [
                    item["node_id"]
                    for item in allocations
                ],
                "weights": dict(self.weights),
            },
        )
