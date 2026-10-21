from __future__ import annotations

import re
from pathlib import Path

from .models import Evidence, ToolEvent, VerificationReport
from .providers import OpenAICompatibleProvider, ProviderError
from .tools import EvidenceSearch, ImageInspector, SourceRater


class VerificationAgent:
    """A transparent plan-act-verify loop with an offline fallback."""

    def __init__(self, corpus_path: str | Path, provider: OpenAICompatibleProvider | None = None):
        self.search = EvidenceSearch(corpus_path)
        self.image_inspector = ImageInspector()
        self.source_rater = SourceRater()
        self.provider = provider

    def verify(self, claim: str, image_path: str | None = None) -> VerificationReport:
        claim = claim.strip()
        if not claim:
            raise ValueError("claim must not be empty")
        trace: list[ToolEvent] = []
        subclaims = self._decompose(claim)
        trace.append(ToolEvent(1, "claim_decomposer", "Break the input into searchable statements", "ok", {"subclaims": subclaims}))

        image_result = None
        if image_path:
            image_result = self.image_inspector.run(image_path)
            trace.append(ToolEvent(2, self.image_inspector.name, "An image was supplied, so inspect its metadata", "ok" if image_result.get("available") else "error", image_result))

        evidence: list[Evidence] = []
        seen = set()
        for subclaim in subclaims:
            for item in self.search.run(subclaim):
                if item.evidence_id not in seen:
                    evidence.append(item)
                    seen.add(item.evidence_id)
        trace.append(ToolEvent(len(trace) + 1, self.search.name, "Retrieve evidence for each subclaim", "ok", {"matches": len(evidence)}))

        ratings = [self.source_rater.run(item.source) for item in evidence]
        trace.append(ToolEvent(len(trace) + 1, self.source_rater.name, "Rate provenance before forming a verdict", "ok", {"ratings": ratings}))

        verdict, confidence, rationale = self._decide(claim, subclaims, evidence, image_result)
        trace.append(ToolEvent(len(trace) + 1, "verifier", "Aggregate evidence and preserve uncertainty", "ok", {"verdict": verdict, "confidence": confidence}))
        limitations = ["The starter corpus is small and is not a live-web index."]
        if image_path:
            limitations.append("Metadata inspection cannot by itself prove whether an image was manipulated.")
        if self.provider is None:
            limitations.append("Offline mode uses lexical retrieval and deterministic decision rules.")
        return VerificationReport(claim, subclaims, verdict, confidence, rationale, evidence, trace, limitations)

    def _decompose(self, claim: str) -> list[str]:
        if self.provider:
            try:
                data = self.provider.complete_json(
                    "Return JSON with a subclaims array. Each item must be independently verifiable. Do not add facts.",
                    claim,
                )
                values = [str(value).strip() for value in data.get("subclaims", []) if str(value).strip()]
                if values:
                    return values[:5]
            except ProviderError:
                pass
        parts = [part.strip(" .") for part in re.split(r"[;；。]|\band\b|并且|以及", claim) if part.strip(" .")]
        return parts[:5] or [claim]

    def _decide(self, claim: str, subclaims: list[str], evidence: list[Evidence], image_result: dict | None):
        if self.provider and evidence:
            try:
                data = self.provider.complete_json(
                    "Judge only from the supplied evidence. Return verdict (supported, refuted, or not_enough_evidence), confidence from 0 to 1, and rationale. Prefer uncertainty.",
                    str({"claim": claim, "subclaims": subclaims, "evidence": [item.__dict__ for item in evidence], "image": image_result}),
                )
                verdict = data.get("verdict", "not_enough_evidence")
                if verdict in {"supported", "refuted", "not_enough_evidence"}:
                    return verdict, max(0.0, min(1.0, float(data.get("confidence", 0.5)))), str(data.get("rationale", ""))
            except (ProviderError, TypeError, ValueError):
                pass
        labelled = [item for item in evidence if item.supports in {"supported", "refuted"}]
        if not labelled:
            return "not_enough_evidence", 0.2, "No sufficiently relevant labelled evidence was retrieved from the local corpus."
        top_score = max(item.score for item in labelled)
        relevant = [item for item in labelled if item.score >= max(1.5, top_score * 0.25)]
        supported = sum(item.score for item in relevant if item.supports == "supported")
        refuted = sum(item.score for item in relevant if item.supports == "refuted")
        total = supported + refuted
        if total == 0 or abs(supported - refuted) / total < 0.2:
            return "not_enough_evidence", 0.45, "Retrieved evidence conflicts, so the system abstains."
        verdict = "supported" if supported > refuted else "refuted"
        confidence = min(0.9, 0.55 + 0.35 * abs(supported - refuted) / total)
        return verdict, confidence, f"The verdict is based on {len(relevant)} relevance-filtered evidence item(s); source ratings remain visible for audit."
