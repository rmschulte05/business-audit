"""The evidence data contract shared by every collector and the scorer.

The whole point of this module is the MEASURED vs NOT_MEASURED distinction.
A Signal is one atomic, named measurement. The scorer only ever divides by the
weight of signals it actually measured, so unmeasured signals lower *confidence*
rather than silently dragging a client's score to zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Status(str, Enum):
    """Whether a signal was actually observed."""

    MEASURED = "measured"          # real evidence captured; points are trustworthy
    NOT_MEASURED = "not_measured"  # could not observe; excluded from score, lowers confidence
    ERROR = "error"                # an attempt was made and failed; treated like not_measured


@dataclass(frozen=True)
class Signal:
    """One atomic measurement within a category.

    points/max_points express the weight of this signal inside its category.
    When status is MEASURED, points is the awarded value in [0, max_points].
    When NOT_MEASURED or ERROR, points is ignored and max_points is excluded
    from the category denominator.
    """

    key: str
    label: str
    status: Status
    max_points: float
    points: float = 0.0
    value: Any = None
    detail: str = ""
    evidence: str = ""          # raw proof: a header value, a quoted line, a URL
    recommendation: str = ""    # what to fix if points < max_points

    def measured(self) -> bool:
        return self.status == Status.MEASURED

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


def measured(
    key: str,
    label: str,
    max_points: float,
    points: float,
    *,
    value: Any = None,
    detail: str = "",
    evidence: str = "",
    recommendation: str = "",
) -> Signal:
    """Build a MEASURED signal, clamping points into [0, max_points]."""
    clamped = max(0.0, min(float(points), float(max_points)))
    return Signal(
        key=key,
        label=label,
        status=Status.MEASURED,
        max_points=float(max_points),
        points=clamped,
        value=value,
        detail=detail,
        evidence=evidence,
        recommendation=recommendation,
    )


def not_measured(
    key: str,
    label: str,
    max_points: float,
    *,
    detail: str = "",
    recommendation: str = "",
) -> Signal:
    """Build a NOT_MEASURED signal. It will be excluded from the score."""
    return Signal(
        key=key,
        label=label,
        status=Status.NOT_MEASURED,
        max_points=float(max_points),
        points=0.0,
        detail=detail or "Not measured by the deterministic engine.",
        recommendation=recommendation,
    )


def errored(
    key: str,
    label: str,
    max_points: float,
    *,
    detail: str = "",
) -> Signal:
    """Build an ERROR signal (an attempt failed). Excluded from the score."""
    return Signal(
        key=key,
        label=label,
        status=Status.ERROR,
        max_points=float(max_points),
        points=0.0,
        detail=detail,
    )


@dataclass(frozen=True)
class CategoryScore:
    """The deterministic result for one GEO category."""

    key: str
    label: str
    signals: tuple[Signal, ...]

    @property
    def measured_signals(self) -> tuple[Signal, ...]:
        return tuple(s for s in self.signals if s.measured())

    @property
    def measured_max(self) -> float:
        return sum(s.max_points for s in self.measured_signals)

    @property
    def total_max(self) -> float:
        return sum(s.max_points for s in self.signals)

    @property
    def earned(self) -> float:
        return sum(s.points for s in self.measured_signals)

    @property
    def score(self) -> float | None:
        """0-100 over MEASURED signals only. None if nothing was measured."""
        if self.measured_max <= 0:
            return None
        return round(self.earned / self.measured_max * 100.0, 1)

    @property
    def confidence(self) -> float:
        """Fraction of this category's weight that was actually measured (0-1)."""
        if self.total_max <= 0:
            return 0.0
        return round(self.measured_max / self.total_max, 3)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "score": self.score,
            "confidence": self.confidence,
            "earned": round(self.earned, 1),
            "measured_max": round(self.measured_max, 1),
            "total_max": round(self.total_max, 1),
            "signals": [s.to_dict() for s in self.signals],
        }


def category(key: str, label: str, signals: list[Signal]) -> CategoryScore:
    return CategoryScore(key=key, label=label, signals=tuple(signals))
