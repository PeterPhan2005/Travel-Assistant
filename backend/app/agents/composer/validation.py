"""Exact closure validation for ResponseComposerOutput."""

from __future__ import annotations

from app.agents.contracts import (
    ResponseComposerOutput,
    ResponseComposerRequest,
)


def validate_response_composer_output(
    output: ResponseComposerOutput,
    request: ResponseComposerRequest,
    deterministic: ResponseComposerOutput,
) -> ResponseComposerOutput:
    """Accept only the complete deterministic normalized output."""
    validated = ResponseComposerOutput.model_validate(
        output.model_dump(mode="python")
    )
    validated.validate_against(request)
    _validate_exact_source_union(validated, request)
    if validated != deterministic:
        raise ValueError(
            "Composer output differs from deterministic approved content."
        )
    return validated


def _validate_exact_source_union(
    output: ResponseComposerOutput,
    request: ResponseComposerRequest,
) -> None:
    claims_by_id = {
        claim.claim_id: claim for claim in request.evidence.claims
    }
    expected_source_ids = tuple(
        sorted(
            {
                source_id
                for claim_id in output.used_claim_ids
                for source_id in claims_by_id[
                    claim_id
                ].supporting_source_ids
            }
        )
    )
    if output.used_source_ids != expected_source_ids:
        raise ValueError(
            "Composer sources must equal the used claims' source union."
        )
