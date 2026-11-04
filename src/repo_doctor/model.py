"""Data model for repo-doctor: weighted results and a scored report."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Status(str, Enum):
    """Outcome of a single check."""

    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"


_FACTOR = {Status.PASS: 1.0, Status.PARTIAL: 0.5, Status.FAIL: 0.0}


@dataclass(frozen=True)
class Result:
    """One evaluated check, with the advice needed to fix it."""

    name: str
    weight: float
    status: Status
    detail: str
    hint: str = ""

    @property
    def earned(self) -> float:
        """Weighted credit for this check."""
        return self.weight * _FACTOR[self.status]


@dataclass
class Report:
    """Every result for one repository root, plus derived score and grade."""

    root: Path
    results: list[Result] = field(default_factory=list)

    @property
    def score(self) -> int:
        """Total points earned, rounded to a whole number out of 100."""
        return round(sum(result.earned for result in self.results))

    @property
    def grade(self) -> str:
        """Letter grade derived from :attr:`score`."""
        score = self.score
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    @property
    def fixes(self) -> list[Result]:
        """Results that did not fully pass, worst first."""
        bad = [r for r in self.results if r.status is not Status.PASS]
        return sorted(bad, key=lambda r: (r.earned - r.weight, r.name))

    def to_dict(self) -> dict[str, Any]:
        """Serializable form used by the ``--json`` flag."""
        return {
            "path": str(self.root),
            "score": self.score,
            "grade": self.grade,
            "checks": [
                {
                    "name": result.name,
                    "weight": result.weight,
                    "status": result.status.value,
                    "detail": result.detail,
                    "hint": result.hint,
                }
                for result in self.results
            ],
        }
