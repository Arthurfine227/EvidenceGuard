from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Verdict = Literal["supported", "refuted", "not_enough_evidence"]


@dataclass
class ToolEvent:
    step: int
    tool: str
    reason: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
class Evidence:
    evidence_id: str
    title: str
    text: str
    source: str
    published_at: str | None = None
    supports: str | None = None
    score: float = 0.0


@dataclass
class VerificationReport:
    claim: str
    subclaims: list[str]
    verdict: Verdict
    confidence: float
    rationale: str
    evidence: list[Evidence]
    trace: list[ToolEvent]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

