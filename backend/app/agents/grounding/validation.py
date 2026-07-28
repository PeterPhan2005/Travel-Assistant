"""Closure validation for model-authored grounding decisions."""

from __future__ import annotations

from app.agents.contracts import (
    GroundingReviewOutput,
    GroundingReviewRequest,
)


def validate_grounding_review_output(
    output: GroundingReviewOutput,
    request: GroundingReviewRequest,
    deterministic: GroundingReviewOutput,
) -> GroundingReviewOutput:
    """Require exact safe claim decisions and closed output approvals."""
    validated = GroundingReviewOutput.model_validate(
        output.model_dump(mode="python")
    )
    validated.validate_against(request)
    if validated.reviewed_claim_ids != deterministic.reviewed_claim_ids:
        raise ValueError("Reviewed claim IDs differ from the request.")
    if validated.status is not deterministic.status:
        raise ValueError("Review status differs from deterministic safety.")
    if validated.approved_claim_ids != deterministic.approved_claim_ids:
        raise ValueError("Claim approvals weaken deterministic safety.")
    if validated.rejected_claims != deterministic.rejected_claims:
        raise ValueError("Claim rejections differ from deterministic rules.")
    if not set(validated.approved_specialist_output_ids).issubset(
        deterministic.approved_specialist_output_ids
    ):
        raise ValueError("Reviewer approved an unsafe specialist output.")
    if validated.warnings != deterministic.warnings:
        raise ValueError("Reviewer returned an unapproved warning.")
    return validated
