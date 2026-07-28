"""Pure deterministic limited Local Culture construction."""

from __future__ import annotations

from enum import StrEnum

from app.agents.contracts import (
    AnswerStatus,
    LocalCultureOutput,
    LocalCultureRequest,
)


class LocalCultureLimitationReason(StrEnum):
    """Closed internal reasons for content-free LocalCultureOutput."""

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MODEL_UNCONFIGURED = "model_unconfigured"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    UNSAFE_GENERALIZATION = "unsafe_generalization"


_LIMITATION_MESSAGES = {
    LocalCultureLimitationReason.INSUFFICIENT_EVIDENCE: (
        "Chưa có đủ bằng chứng văn hóa đã được phê duyệt để hướng dẫn an toàn."
    ),
    LocalCultureLimitationReason.MODEL_UNCONFIGURED: (
        "Tính năng hướng dẫn văn hóa trực tuyến hiện chưa được cấu hình."
    ),
    LocalCultureLimitationReason.MODEL_UNAVAILABLE: (
        "Tạm thời chưa thể tạo hướng dẫn văn hóa an toàn từ bằng chứng đã có."
    ),
    LocalCultureLimitationReason.INVALID_MODEL_OUTPUT: (
        "Chưa thể xác nhận hướng dẫn văn hóa đáp ứng đầy đủ yêu cầu an toàn."
    ),
    LocalCultureLimitationReason.UNSAFE_GENERALIZATION: (
        "Chưa thể cung cấp hướng dẫn vì nội dung có nguy cơ khái quát thiếu tôn trọng."
    ),
}


def build_limited_local_culture(
    request: LocalCultureRequest,
    reason: LocalCultureLimitationReason,
) -> LocalCultureOutput:
    """Return the same validated content-free result for a request/reason."""
    output = LocalCultureOutput(
        status=AnswerStatus.LIMITED,
        guidance=(),
        respectful_caution=None,
        limitation_reason=_LIMITATION_MESSAGES[reason],
    )
    return output.validate_against(request)


def limitation_reason_code(output: LocalCultureOutput) -> str:
    """Map only application-owned messages to a safe logging code."""
    for reason, message in _LIMITATION_MESSAGES.items():
        if output.limitation_reason == message:
            return reason.value
    return "model_limited"
