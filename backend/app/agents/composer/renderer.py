"""Pure deterministic rendering from approved composer input only."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.agents.contracts import (
    AnswerStatus,
    DiscoverySpecialistOutput,
    FactKind,
    FactualClaim,
    ItinerarySpecialistOutput,
    LocalCultureSpecialistOutput,
    NarrationSpecialistOutput,
    PoiPresentationItem,
    PriceFact,
    ResponseComposerOutput,
    ResponseComposerRequest,
)

SAFE_FALLBACK_TEXT = (
    "Chưa có đủ thông tin đã được phê duyệt để trả lời an toàn."
)

_MAX_FINAL_TEXT_LENGTH = 6000
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
    "chain of thought",
    "discovery",
    "exception",
    "grounding reviewer",
    "grounding_reviewer",
    "local_culture",
    "model output",
    "narration",
    "openai",
    "prompt",
    "response composer",
    "response_composer",
    "router",
    "runner.run",
    "sdk",
    "system message",
    "tool call",
)


@dataclass
class _TextBuilder:
    pieces: list[str] = field(default_factory=list)
    normalized_content: set[str] = field(default_factory=set)
    used_claim_ids: set[str] = field(default_factory=set)
    started_sections: set[str] = field(default_factory=set)

    def add(
        self,
        section: str,
        text: str,
        claim_ids: tuple[str, ...] = (),
    ) -> bool:
        """Add one whole safe fragment without truncating approved content."""
        if not _is_safe_public_fragment(text):
            return False
        normalized = _normalize_content(text)
        if normalized in self.normalized_content:
            self.used_claim_ids.update(claim_ids)
            return True

        additions = [text]
        if section not in self.started_sections:
            additions.insert(0, section)
        candidate = "\n".join((*self.pieces, *additions))
        if len(candidate) > _MAX_FINAL_TEXT_LENGTH:
            return False

        self.pieces.extend(additions)
        self.started_sections.add(section)
        self.normalized_content.add(normalized)
        self.used_claim_ids.update(claim_ids)
        return True

    def render(self) -> str:
        """Return bounded deterministic text or the fixed safe fallback."""
        return "\n".join(self.pieces) if self.pieces else SAFE_FALLBACK_TEXT


def build_deterministic_response(
    request: ResponseComposerRequest,
) -> ResponseComposerOutput:
    """Render one byte-deterministic result from approved input only."""
    claims_by_id = {
        claim.claim_id: claim
        for claim in request.evidence.claims
        if claim.claim_id in set(request.approved_claim_ids)
    }
    builder = _TextBuilder()
    used_claim_ids: set[str] = set()

    _render_narration(request, builder)
    _render_local_culture(request, builder)
    _render_itinerary(request, builder)

    poi_items, discovery_claim_ids = _build_poi_items(
        request,
        claims_by_id,
    )
    used_claim_ids.update(discovery_claim_ids)
    _render_discovery(request, builder)

    used_claim_ids.update(builder.used_claim_ids)
    for claim_id in request.approved_claim_ids:
        if claim_id in used_claim_ids:
            continue
        claim = claims_by_id[claim_id]
        if builder.add(
            "Thông tin bổ sung:",
            claim.statement,
            (claim_id,),
        ):
            used_claim_ids.add(claim_id)

    used_claim_ids.update(builder.used_claim_ids)
    sorted_claim_ids = tuple(sorted(used_claim_ids))
    source_ids = _source_union(sorted_claim_ids, claims_by_id)
    return ResponseComposerOutput(
        final_text=builder.render(),
        poi_items=poi_items,
        warnings=request.warnings,
        used_claim_ids=sorted_claim_ids,
        used_source_ids=source_ids,
    )


def _render_narration(
    request: ResponseComposerRequest,
    builder: _TextBuilder,
) -> None:
    for specialist in request.approved_specialist_outputs:
        if not isinstance(specialist, NarrationSpecialistOutput):
            continue
        output = specialist.output
        if output.status is not AnswerStatus.COMPLETE:
            continue
        claim_ids = output.used_claim_ids
        if output.narration_text is not None:
            builder.add(
                "Phần thuyết minh:",
                output.narration_text,
                claim_ids,
            )
        for key_point in output.key_points:
            builder.add("Các điểm chính:", key_point, claim_ids)


def _render_local_culture(
    request: ResponseComposerRequest,
    builder: _TextBuilder,
) -> None:
    for specialist in request.approved_specialist_outputs:
        if not isinstance(specialist, LocalCultureSpecialistOutput):
            continue
        output = specialist.output
        if output.status is not AnswerStatus.COMPLETE:
            continue
        for guidance in output.guidance:
            builder.add(
                "Thông tin văn hóa địa phương:",
                guidance.text,
                guidance.claim_ids,
            )
        if output.respectful_caution is not None:
            builder.add(
                "Lưu ý ứng xử:",
                output.respectful_caution,
            )


def _render_itinerary(
    request: ResponseComposerRequest,
    builder: _TextBuilder,
) -> None:
    for specialist in request.approved_specialist_outputs:
        if not isinstance(specialist, ItinerarySpecialistOutput):
            continue
        output = specialist.output
        for item in output.items:
            text = (
                f"{item.start_local_time.isoformat(timespec='minutes')}–"
                f"{item.end_local_time.isoformat(timespec='minutes')}: "
                f"{item.title}"
            )
            builder.add(
                "Lịch trình nháp:",
                text,
                item.supporting_claim_ids,
            )
        for assumption in output.assumptions:
            builder.add("Giả định của lịch trình nháp:", assumption)


def _render_discovery(
    request: ResponseComposerRequest,
    builder: _TextBuilder,
) -> None:
    seen_poi_ids: set[str] = set()
    for specialist in request.approved_specialist_outputs:
        if not isinstance(specialist, DiscoverySpecialistOutput):
            continue
        for candidate in specialist.output.candidates:
            if candidate.id in seen_poi_ids:
                continue
            seen_poi_ids.add(candidate.id)
            builder.add(
                "Các địa điểm:",
                (
                    f"Tên địa điểm: {candidate.canonical_name}. "
                    f"Loại: {candidate.category}."
                ),
            )


def _build_poi_items(
    request: ResponseComposerRequest,
    claims_by_id: dict[str, FactualClaim],
) -> tuple[tuple[PoiPresentationItem, ...], set[str]]:
    items: list[PoiPresentationItem] = []
    used_claim_ids: set[str] = set()
    seen_poi_ids: set[str] = set()
    approved_ids = set(request.approved_claim_ids)

    for specialist in request.approved_specialist_outputs:
        if not isinstance(specialist, DiscoverySpecialistOutput):
            continue
        discovery_claims = tuple(
            claim
            for claim in specialist.output.evidence.claims
            if claim.claim_id in approved_ids
        )
        for candidate in specialist.output.candidates:
            if candidate.id in seen_poi_ids:
                continue
            seen_poi_ids.add(candidate.id)
            price_claim = _single_price_claim(
                candidate.id,
                request.approved_claim_ids,
                claims_by_id,
            )
            opening_hours = _safe_opening_hours(
                candidate.opening_hours_summary
            )
            items.append(
                PoiPresentationItem(
                    poi_id=candidate.id,
                    canonical_name=candidate.canonical_name,
                    category=candidate.category,
                    address=candidate.address,
                    distance_metres=candidate.distance_metres,
                    rating=candidate.rating,
                    rating_count=candidate.rating_count,
                    price=(
                        price_claim.price
                        if price_claim is not None
                        else None
                    ),
                    opening_hours_summary=opening_hours,
                )
            )
            visible_fact_kinds = {
                FactKind.IDENTITY,
                FactKind.CATEGORY,
            }
            if candidate.address is not None:
                visible_fact_kinds.add(FactKind.LOCATION)
            if candidate.distance_metres is not None:
                visible_fact_kinds.add(FactKind.DISTANCE)
            if candidate.rating is not None or candidate.rating_count is not None:
                visible_fact_kinds.add(FactKind.RATING)
            if opening_hours is not None:
                visible_fact_kinds.add(FactKind.OPENING_HOURS)
            used_claim_ids.update(
                claim.claim_id
                for claim in discovery_claims
                if claim.poi_id == candidate.id
                and claim.fact_kind in visible_fact_kinds
            )
            if price_claim is not None:
                used_claim_ids.add(price_claim.claim_id)
    return tuple(items), used_claim_ids


def _single_price_claim(
    poi_id: str,
    approved_claim_ids: tuple[str, ...],
    claims_by_id: dict[str, FactualClaim],
) -> FactualClaim | None:
    prices = tuple(
        claims_by_id[claim_id]
        for claim_id in approved_claim_ids
        if claims_by_id[claim_id].poi_id == poi_id
        and claims_by_id[claim_id].fact_kind is FactKind.PRICE
        and isinstance(claims_by_id[claim_id].price, PriceFact)
    )
    return prices[0] if len(prices) == 1 else None


def _safe_opening_hours(value: str | None) -> str | None:
    if value is None or len(value) > 240:
        return None
    return value if _is_safe_public_fragment(value) else None


def _source_union(
    claim_ids: tuple[str, ...],
    claims_by_id: dict[str, FactualClaim],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                source_id
                for claim_id in claim_ids
                for source_id in claims_by_id[
                    claim_id
                ].supporting_source_ids
            }
        )
    )


def _normalize_content(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE.sub(" ", normalized).strip()


def _is_safe_public_fragment(value: str) -> bool:
    if "<" in value or ">" in value:
        return False
    if _MARKDOWN_LINE.search(value) or _MARKDOWN_INLINE.search(value):
        return False
    normalized = _normalize_content(value)
    return not any(term in normalized for term in _INTERNAL_TERMS)
