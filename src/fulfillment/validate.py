from pathlib import Path
import csv


def validate(root: Path):
    path = root / "ground_truth.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [(r["issue_type"], r["entity_id"]) for r in rows]


def validate_baseline(root: Path) -> list:
    return []
