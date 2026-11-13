from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    node_id: str
    score: float
    feasible: bool


def choose_best(candidates: list[Candidate]) -> Candidate | None:
    feasible = [c for c in candidates if c.feasible]
    return min(feasible, key=lambda c: (c.score, c.node_id)) if feasible else None
