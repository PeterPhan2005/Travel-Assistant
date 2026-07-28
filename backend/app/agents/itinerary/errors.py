"""Sanitized errors for total Itinerary execution failures."""

from enum import StrEnum

from app.agents.contracts import AgentFailure, AgentKind, FailureCode


class ItineraryFailureReason(StrEnum):
    """Stable internal reasons for deterministic planning failure."""

    NO_USABLE_CANDIDATES = "no_usable_candidates"
    UNSATISFIABLE_CONSTRAINTS = "unsatisfiable_constraints"
    UNSATISFIABLE_TIME_WINDOW = "unsatisfiable_time_window"


_FAILURE_MESSAGES = {
    ItineraryFailureReason.NO_USABLE_CANDIDATES: (
        "Không có địa điểm phù hợp để tạo lịch trình nháp."
    ),
    ItineraryFailureReason.UNSATISFIABLE_CONSTRAINTS: (
        "Không thể tạo lịch trình nháp với các ràng buộc đã chọn."
    ),
    ItineraryFailureReason.UNSATISFIABLE_TIME_WINDOW: (
        "Khung giờ đã chọn không đủ để tạo lịch trình nháp."
    ),
}


class ItineraryExecutionError(Exception):
    """A total planning failure carrying only one stable typed issue."""

    __slots__ = ("failure", "reason")

    def __init__(self, reason: ItineraryFailureReason) -> None:
        self.reason = reason
        self.failure = AgentFailure(
            stage=AgentKind.ITINERARY,
            code=FailureCode.INVALID_INPUT,
            message=_FAILURE_MESSAGES[reason],
            retryable=False,
        )
        super().__init__(reason.value)
