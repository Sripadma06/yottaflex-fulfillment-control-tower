from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Mapping


@dataclass(frozen=True)
class PromiseRequest:
    order_id: str
    order_ts: datetime
    service_level: str
    destination_zone: str
    processing_days: int = 1
    transit_days: int = 0


@dataclass(frozen=True)
class PromiseResult:
    order_id: str
    promised_date: date
    processing_days: int
    transit_days: int
    total_days: int
    service_level: str
    destination_zone: str
    cutoff_applied: bool
    holiday_days_skipped: int
    non_operating_days_skipped: int
    reasoning: dict[str, object]


class DeliveryPromiseEngine:
    SERVICE_TARGET_DAYS = {
        "SL-SAME": 1,
        "SL-EXP": 2,
        "SL-STD": 5,
        "SAME_DAY": 1,
        "EXPRESS": 2,
        "STANDARD": 5,
    }

    def __init__(
        self,
        holidays: set[date] | None = None,
        operating_weekdays: set[int] | frozenset[int] | None = None,
        cutoff_times: Mapping[str, time] | None = None,
    ) -> None:
        self.holidays = holidays or set()
        self.operating_weekdays = (
            frozenset({0, 1, 2, 3, 4})
            if operating_weekdays is None
            else frozenset(operating_weekdays)
        )
        self.cutoff_times = dict(cutoff_times or {})

    def calculate(
        self,
        request: PromiseRequest,
    ) -> PromiseResult:
        if request.processing_days < 0:
            raise ValueError("Processing days cannot be negative.")

        if request.transit_days < 0:
            raise ValueError("Transit days cannot be negative.")

        cutoff_applied = self._cutoff_passed(request)

        start = request.order_ts

        if cutoff_applied:
            start = start + timedelta(days=1)

        processing_end, processing_holidays, processing_non_operating = (
            self._add_operating_days(
                start,
                request.processing_days,
            )
        )

        transit_end, transit_holidays, transit_non_operating = (
            self._add_operating_days(
                processing_end,
                request.transit_days,
            )
        )

        promised_date = transit_end.date()

        holiday_days_skipped = (
            processing_holidays + transit_holidays
        )

        non_operating_days_skipped = (
            processing_non_operating + transit_non_operating
        )

        return PromiseResult(
            order_id=request.order_id,
            promised_date=promised_date,
            processing_days=request.processing_days,
            transit_days=request.transit_days,
            total_days=request.processing_days + request.transit_days,
            service_level=request.service_level,
            destination_zone=request.destination_zone,
            cutoff_applied=cutoff_applied,
            holiday_days_skipped=holiday_days_skipped,
            non_operating_days_skipped=non_operating_days_skipped,
            reasoning={
                "order_timestamp": request.order_ts.isoformat(),
                "promised_date": promised_date.isoformat(),
                "processing_days": request.processing_days,
                "transit_days": request.transit_days,
                "cutoff_applied": cutoff_applied,
                "holiday_days_skipped": holiday_days_skipped,
                "non_operating_days_skipped": non_operating_days_skipped,
                "target_service_days": self.SERVICE_TARGET_DAYS.get(
                    request.service_level.upper(),
                ),
            },
        )

    def _cutoff_passed(self, request: PromiseRequest) -> bool:
        cutoff = self.cutoff_times.get(request.service_level)

        if cutoff is None:
            return False

        return request.order_ts.time() > cutoff

    def _add_operating_days(
        self,
        start: datetime,
        days: int,
    ) -> tuple[datetime, int, int]:
        current = start
        completed = 0
        holiday_days_skipped = 0
        non_operating_days_skipped = 0

        while completed < days:
            current += timedelta(days=1)

            if current.date() in self.holidays:
                holiday_days_skipped += 1
                continue

            if current.weekday() not in self.operating_weekdays:
                non_operating_days_skipped += 1
                continue

            completed += 1

        return (
            current,
            holiday_days_skipped,
            non_operating_days_skipped,
        )
