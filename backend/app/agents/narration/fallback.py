"""Pure deterministic limited narration construction."""

from __future__ import annotations

from enum import StrEnum

from app.agents.contracts import (
    AnswerStatus,
    NarrationOutput,
    NarrationRequest,
)


class NarrationLimitationReason(StrEnum):
    """Closed internal reasons for a content-free NarrationOutput."""

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MODEL_UNCONFIGURED = "model_unconfigured"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_OUTPUT = "invalid_model_output"


_LIMITATION_MESSAGES = {
    NarrationLimitationReason.INSUFFICIENT_EVIDENCE: (
        "Chưa có đủ bằng chứng đã được phê duyệt để tạo thuyết minh an toàn."
    ),
    NarrationLimitationReason.MODEL_UNCONFIGURED: (
        "Tính năng thuyết minh trực tuyến hiện chưa được cấu hình."
    ),
    NarrationLimitationReason.MODEL_UNAVAILABLE: (
        "Tạm thời chưa thể tạo thuyết minh an toàn từ bằng chứng đã cung cấp."
    ),
    NarrationLimitationReason.INVALID_MODEL_OUTPUT: (
        "Chưa thể xác nhận thuyết minh đáp ứng đầy đủ yêu cầu an toàn."
    ),
}


def build_limited_narration(
    request: NarrationRequest,
    reason: NarrationLimitationReason,
) -> NarrationOutput:
    """Return the same validated content-free result for a request/reason."""
    output = NarrationOutput(
        status=AnswerStatus.LIMITED,
        narration_text=None,
        key_points=(),
        used_source_ids=(),
        used_claim_ids=(),
        limitation_reason=_LIMITATION_MESSAGES[reason],
    )
    return output.validate_against(request)


def limitation_reason_code(output: NarrationOutput) -> str:
    """Map only known public fallback messages back to a safe log code."""
    for reason, message in _LIMITATION_MESSAGES.items():
        if output.limitation_reason == message:
            return reason.value
    return "model_limited"
