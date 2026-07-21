# Grounding Reviewer Agent

## Purpose

Review specialist outputs before the final response.

## Input

- Deterministically ranked discovery results.
- Structured outputs from any selected optional specialists.
- Source metadata.
- Product response rules.

## Output

- Approved facts.
- Rejected facts with reason.
- Missing required disclosures.
- Severity.
- Whether the response can proceed.

## Allowed tools

- Source metadata lookup.
- Freshness policy checker.

## Forbidden

- No new POI discovery.
- No rewriting the final response.
- No unsupported correction.

## Fallback

Reject uncertain claims rather than guessing.
