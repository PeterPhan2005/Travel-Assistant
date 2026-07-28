"""Pure evidence-sufficiency and NarrationOutput closure checks."""

from __future__ import annotations

import re
import unicodedata

from app.agents.contracts import (
    AnswerStatus,
    FactualClaim,
    NarrationOutput,
    NarrationRequest,
)

_WHITESPACE = re.compile(r"\s+")
_MARKDOWN_LINE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s|[-+*]\s|\d+[.)]\s|>\s?|"
    r"={3,}\s*$|-{3,}\s*$|\|.*\|\s*$)",
    re.MULTILINE,
)
_MARKDOWN_INLINE = re.compile(
    r"`|\*\*|__|!\[|\[[^\]]+\]\([^)]+\)|&(?:lt|gt);|"
    r"\|[^|\n]+\|[^|\n]+\|",
    re.IGNORECASE,
)
_INTERNAL_TERMS = (
    "agent",
    "chain of thought",
    "exception",
    "grounding reviewer",
    "model output",
    "openai",
    "prompt",
    "response composer",
    "runner.run",
    "sdk",
    "system message",
    "tool call",
)


def usable_claims(request: NarrationRequest) -> tuple[FactualClaim, ...]:
    """Return only claims explicitly scoped to this request's POI."""
    known_sources = request.evidence.source_ids
    return tuple(
        claim
        for claim in request.evidence.claims
        if claim.poi_id == request.poi.poi_id
        and set(claim.supporting_source_ids).issubset(known_sources)
    )


def has_sufficient_evidence(request: NarrationRequest) -> bool:
    """Decide whether a complete model attempt is permitted."""
    claims = usable_claims(request)
    if not claims or not request.evidence.sources:
        return False
    return any(claim.supporting_source_ids for claim in claims)


def validate_narration_output(
    output: NarrationOutput,
    request: NarrationRequest,
) -> NarrationOutput:
    """Revalidate and close one output over exactly one narration request."""
    validated = NarrationOutput.model_validate(
        output.model_dump(mode="python")
    )
    validated.validate_against(request)

    if validated.status is AnswerStatus.LIMITED:
        if validated.limitation_reason is None:
            raise ValueError("Limited narration requires a safe reason.")
        _validate_public_text(validated.limitation_reason)
        return validated

    claims_by_id = {
        claim.claim_id: claim
        for claim in usable_claims(request)
    }
    if not set(validated.used_claim_ids).issubset(claims_by_id):
        raise ValueError("Narration uses a claim not scoped to the POI.")

    expected_source_ids = tuple(
        sorted(
            {
                source_id
                for claim_id in validated.used_claim_ids
                for source_id in claims_by_id[
                    claim_id
                ].supporting_source_ids
            }
        )
    )
    if validated.used_source_ids != expected_source_ids:
        raise ValueError(
            "Narration sources must equal the used claims' source union."
        )

    normalized_key_points = tuple(
        _normalize_unique_text(key_point)
        for key_point in validated.key_points
    )
    if len(normalized_key_points) != len(set(normalized_key_points)):
        raise ValueError("Narration key points must be uniquely normalized.")

    if validated.narration_text is None:
        raise ValueError("Complete narration requires text.")
    _validate_public_text(validated.narration_text)
    for key_point in validated.key_points:
        _validate_public_text(key_point)
    return validated


def _normalize_unique_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE.sub(" ", normalized).strip()


def _validate_public_text(value: str) -> None:
    if _MARKDOWN_LINE.search(value) or _MARKDOWN_INLINE.search(value):
        raise ValueError("Narration content must be plain text.")
    normalized = _normalize_unique_text(value)
    if any(term in normalized for term in _INTERNAL_TERMS):
        raise ValueError("Narration content exposes internal terminology.")
