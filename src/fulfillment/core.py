from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PromiseResult:
    promised_date: date
    trace: dict


def working_day_after(start: date, days: int) -> date:
    current = start
    remaining = days
    while remaining:
        current = current.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:
            remaining -= 1
    return current
