"""Pure evidence sufficiency, safety, and LocalCultureOutput closure."""

from __future__ import annotations

import re
import unicodedata

from app.agents.contracts import (
    AnswerStatus,
    FactKind,
    FactualClaim,
    LocalCultureOutput,
    LocalCultureRequest,
)

FIXED_RESPECTFUL_CAUTION = (
    "Phong tục có thể khác nhau theo hoàn cảnh; khi chưa chắc chắn, "
    "hãy quan sát và hỏi một cách lịch sự."
)

_WHITESPACE = re.compile(r"\s+")
_MARKDOWN_LINE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s|[-+*]\s|\d+[.)]\s|>\s?|"
    r"={3,}\s*$|-{3,}\s*$|\|.*\|\s*$)",
    re.MULTILINE,
)
_MARKDOWN_INLINE = re.compile(
    r"`|\*\*|__|!\[|\[[^\]]+\]\([^)]+\)|&(?:lt|gt);|"
    r"\|[^|\n]+\|[^|\n]+\||(?<!\w)_[^_\n]+_(?!\w)|"
    r"(?<!\w)\*[^*\n]+\*(?!\w)",
    re.IGNORECASE,
)
_INTERNAL_TERMS = (
    "agent",
    "api key",
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
    "token",
    "tool call",
)
_ABSOLUTE_GENERALIZATIONS = (
    "ai cung",
    "all locals",
    "all people",
    "everyone",
    "every thai person",
    "every vietnamese person",
    "nguoi dia phuong luon",
    "nguoi thai luon",
    "nguoi viet luon",
    "people always",
    "people never",
    "tat ca nguoi dan",
)
_IDENTITY_GROUP_TERMS = (
    "dan toc",
    "ethnic",
    "gioi tinh",
    "men are",
    "muslims are",
    "nationality",
    "nguoi cao tuoi",
    "nguoi ngheo",
    "nguoi theo dao",
    "nguoi thai",
    "nguoi viet",
    "phu nu",
    "profession",
    "religion",
    "social class",
    "thai people",
    "thai are",
    "the thai",
    "the vietnamese",
    "vietnamese are",
    "vietnamese people",
    "women are",
)
_PERSONALITY_TERMS = (
    "aggressive",
    "cham chi",
    "dishonest",
    "diu dang",
    "emotional",
    "friendly",
    "generous",
    "gentle",
    "hardworking",
    "hien lanh",
    "hieu khach",
    "honest",
    "intelligent",
    "kind",
    "keo kiet",
    "khon ngoan",
    "lazy",
    "lich su",
    "polite",
    "rude",
    "stingy",
    "submissive",
    "than thien",
    "thong minh",
)
_DEMEANING_OR_COMPARATIVE_TERMS = (
    "backward",
    "better than",
    "exotic",
    "ha dang",
    "inferior",
    "kem hon",
    "ky la",
    "lac hau",
    "man ro",
    "primitive",
    "savage",
    "superior",
    "thuong dang",
    "tot hon",
    "uncivilized",
    "vuot troi",
    "worse than",
)
_LEGAL_MEDICAL_SAFETY_TERMS = (
    "bac si",
    "call the police",
    "canh sat",
    "cap cuu",
    "chan doan",
    "chinh quyen bat buoc",
    "dieu tri",
    "doctor",
    "diagnose",
    "emergency instruction",
    "go to emergency",
    "go to hospital",
    "illegal",
    "law says",
    "law requires",
    "legal",
    "legal obligation",
    "medical",
    "medicine",
    "phap luat",
    "self defense",
    "so cuu",
    "take medication",
    "take medicine",
    "theo luat",
    "thuoc dieu tri",
    "treatment",
    "tu ve",
    "uong thuoc",
)
_RESTRICTED_TOPICS = (
    ("religion", ("dao", "religion", "religious", "ton giao")),
    ("dress", ("che vai", "dress", "quan ao", "trang phuc")),
    ("tipping", ("tip", "tipping", "tien boa")),
    ("bargaining", ("bargain", "mac ca", "tra gia")),
    ("gesture", ("cu chi", "gesture")),
    ("food", ("an kieng", "food restriction", "kieng an")),
    ("photography", ("chup anh", "photography")),
    ("temple", ("den tho", "temple", "vao den", "chua")),
    ("government", ("chinh quyen", "government")),
)


class UnsafeLocalCultureOutputError(ValueError):
    """Signal an obvious stereotype, generalization, or unsafe assertion."""


def usable_claims(
    request: LocalCultureRequest,
) -> tuple[FactualClaim, ...]:
    """Return source-closed culture/etiquette claims safe to show the model."""
    known_sources = request.evidence.source_ids
    return tuple(
        claim
        for claim in request.evidence.claims
        if claim.fact_kind in {FactKind.CULTURE, FactKind.ETIQUETTE}
        and bool(claim.supporting_source_ids)
        and set(claim.supporting_source_ids).issubset(known_sources)
        and not _contains_disallowed_content(claim.statement)
    )


def has_sufficient_evidence(request: LocalCultureRequest) -> bool:
    """Decide whether a complete model attempt is permitted."""
    claims = usable_claims(request)
    return bool(request.evidence.sources and claims)


def validate_local_culture_output(
    output: LocalCultureOutput,
    request: LocalCultureRequest,
) -> LocalCultureOutput:
    """Revalidate and close one output over exactly one culture request."""
    validated = LocalCultureOutput.model_validate(
        output.model_dump(mode="python")
    )
    validated.validate_against(request)

    if validated.status is AnswerStatus.LIMITED:
        if validated.limitation_reason is None:
            raise ValueError("Limited culture output requires a safe reason.")
        _validate_public_text(validated.limitation_reason)
        if _contains_disallowed_content(validated.limitation_reason):
            raise UnsafeLocalCultureOutputError(
                "Limited reason contains unsafe cultural content."
            )
        return validated

    expected_ids = tuple(
        f"culture-guidance-{index:03d}"
        for index in range(1, len(validated.guidance) + 1)
    )
    actual_ids = tuple(item.guidance_id for item in validated.guidance)
    if actual_ids != expected_ids:
        raise ValueError("Culture guidance IDs must be canonical and sequential.")

    if validated.respectful_caution not in {
        None,
        FIXED_RESPECTFUL_CAUTION,
    }:
        raise ValueError("Respectful caution must use the fixed generic text.")

    claims_by_id = {
        claim.claim_id: claim
        for claim in usable_claims(request)
    }
    normalized_guidance: list[str] = []
    for item in validated.guidance:
        if not set(item.claim_ids).issubset(claims_by_id):
            raise UnsafeLocalCultureOutputError(
                "Guidance uses an unsafe or unavailable claim."
            )
        expected_source_ids = tuple(
            sorted(
                {
                    source_id
                    for claim_id in item.claim_ids
                    for source_id in claims_by_id[
                        claim_id
                    ].supporting_source_ids
                }
            )
        )
        if item.source_ids != expected_source_ids:
            raise ValueError(
                "Guidance sources must equal the used claims' source union."
            )
        _validate_public_text(item.text)
        supporting_statements = tuple(
            claims_by_id[claim_id].statement
            for claim_id in item.claim_ids
        )
        _validate_guidance_safety(item.text, supporting_statements)
        normalized_guidance.append(_normalize_text(item.text))

    if len(normalized_guidance) != len(set(normalized_guidance)):
        raise ValueError("Guidance text must be uniquely normalized.")
    return validated


def _validate_public_text(value: str) -> None:
    if _MARKDOWN_LINE.search(value) or _MARKDOWN_INLINE.search(value):
        raise ValueError("Local Culture content must be plain text.")
    normalized = _normalize_text(value)
    if any(term in normalized for term in _INTERNAL_TERMS):
        raise ValueError("Local Culture content exposes internal terminology.")


def _validate_guidance_safety(
    text: str,
    supporting_statements: tuple[str, ...],
) -> None:
    normalized = _normalize_search_text(text)
    if _contains_disallowed_content(text):
        raise UnsafeLocalCultureOutputError(
            "Guidance contains an unsafe generalization or assertion."
        )

    normalized_claims = " ".join(
        _normalize_search_text(statement)
        for statement in supporting_statements
    )
    for _, terms in _RESTRICTED_TOPICS:
        if any(term in normalized for term in terms) and not any(
            term in normalized_claims for term in terms
        ):
            raise UnsafeLocalCultureOutputError(
                "Guidance invents an unsupported cultural requirement."
            )


def _contains_disallowed_content(value: str) -> bool:
    normalized = _normalize_search_text(value)
    if any(term in normalized for term in _ABSOLUTE_GENERALIZATIONS):
        return True
    if any(
        term in normalized
        for term in _DEMEANING_OR_COMPARATIVE_TERMS
    ):
        return True
    if any(term in normalized for term in _LEGAL_MEDICAL_SAFETY_TERMS):
        return True
    return (
        any(term in normalized for term in _IDENTITY_GROUP_TERMS)
        and any(term in normalized for term in _PERSONALITY_TERMS)
    )


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE.sub(" ", normalized).strip()


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", _normalize_text(value))
    without_marks = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    ).replace("đ", "d")
    return _WHITESPACE.sub(" ", without_marks).strip()
