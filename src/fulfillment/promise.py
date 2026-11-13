from datetime import date
from .core import working_day_after, PromiseResult


def calculate_promise(order_date: date, transit_days: int, buffer_days: int = 0) -> PromiseResult:
    promised = working_day_after(order_date, transit_days + buffer_days)
    return PromiseResult(
        promised_date=promised,
        trace={
            "order_date": order_date.isoformat(),
            "transit_days": transit_days,
            "buffer_days": buffer_days,
            "promised_date": promised.isoformat(),
        },
    )
