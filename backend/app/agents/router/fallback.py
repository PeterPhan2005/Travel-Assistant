"""Pure deterministic fallback matching for all closed MVP router intents."""

from __future__ import annotations

import re
import unicodedata

from app.agents.contracts import (
    IntentKind,
    RouterEntities,
    RouterOutput,
    RouterRequest,
    SpecialistKind,
    SupportedCity,
)

_WHITESPACE = re.compile(r"\s+")

# Precedence is deliberate and tested: itinerary, culture, nearby, POI
# information, general travel help, then unsupported.
_ITINERARY_SIGNALS = (
    "lich trinh",
    "len ke hoach",
    "ke hoach tham quan",
    "di dau trong mot ngay",
    "itinerary",
    "travel plan",
    "day plan",
    "half day plan",
)
_CULTURE_SIGNALS = (
    "van hoa",
    "phong tuc",
    "nghi thuc",
    "phep lich su",
    "dieu nen lam",
    "dieu khong nen lam",
    "culture",
    "etiquette",
    "customs",
    "local manners",
)
_NEARBY_SIGNALS = (
    "gan day",
    "gan toi",
    "xung quanh",
    "o quanh day",
    "nearby",
    "near me",
    "around me",
    "places close by",
)
_POI_INFORMATION_SIGNALS = (
    "gioi thieu",
    "thong tin ve",
    "ke ve",
    "lich su cua",
    "tell me about",
    "information about",
    "history of",
    "what is",
)
_POI_DIRECT_SIGNALS = (
    "dia diem nay",
    "noi nay",
    "this place",
)
_TRAVEL_CONTEXT_SIGNALS = (
    "dia diem",
    "diem tham quan",
    "bao tang",
    "cho",
    "chua",
    "den",
    "nha tho",
    "cung dien",
    "cong vien",
    "quan an",
    "nha hang",
    "mon an",
    "destination",
    "attraction",
    "landmark",
    "museum",
    "market",
    "temple",
    "pagoda",
    "church",
    "palace",
    "park",
    "restaurant",
    "food",
    "dish",
    "wat",
    "hcmc",
    "ho chi minh",
    "thanh pho ho chi minh",
    "sai gon",
    "saigon",
    "bangkok",
    "bang coc",
)
_GENERAL_TRAVEL_SIGNALS = (
    "du lich",
    "chuyen di",
    "tham quan",
    "travel",
    "tourism",
    "visit",
    "trip",
)

_HCMC_ALIASES = (
    "hcmc",
    "ho chi minh city",
    "ho chi minh",
    "thanh pho ho chi minh",
    "sai gon",
    "saigon",
)
_BANGKOK_ALIASES = (
    "bangkok",
    "bang coc",
)

_UNSUPPORTED_REASON = (
    "Vui lòng nêu rõ nhu cầu du lịch bạn muốn được hỗ trợ."
)


def match_router_fallback(request: RouterRequest) -> RouterOutput:
    """Return the same validated router output for the same validated request."""
    normalized_query = _normalize_for_matching(request.user_query)
    intent = _match_intent(normalized_query)
    city = request.city or _extract_city(normalized_query)
    entities = RouterEntities(
        city=city,
        category=None,
        query_term=None,
        referenced_poi_ids=(),
        itinerary_constraints=None,
    )

    if intent is IntentKind.NEARBY_DISCOVERY:
        return RouterOutput(
            primary_intent=intent,
            entities=entities,
            specialist_plan=(SpecialistKind.DISCOVERY,),
            discovery_required=True,
            clarification_reason=None,
        )
    if intent is IntentKind.POI_INFORMATION:
        return RouterOutput(
            primary_intent=intent,
            entities=entities,
            specialist_plan=(SpecialistKind.NARRATION,),
            discovery_required=False,
            clarification_reason=None,
        )
    if intent is IntentKind.LOCAL_CULTURE:
        return RouterOutput(
            primary_intent=intent,
            entities=entities,
            specialist_plan=(SpecialistKind.LOCAL_CULTURE,),
            discovery_required=False,
            clarification_reason=None,
        )
    if intent is IntentKind.ITINERARY_DRAFTING:
        return RouterOutput(
            primary_intent=intent,
            entities=entities,
            specialist_plan=(
                SpecialistKind.DISCOVERY,
                SpecialistKind.ITINERARY,
            ),
            discovery_required=True,
            clarification_reason=None,
        )
    if intent is IntentKind.GENERAL_TRAVEL_HELP:
        return RouterOutput(
            primary_intent=intent,
            entities=entities,
            specialist_plan=(),
            discovery_required=False,
            clarification_reason=None,
        )
    return RouterOutput(
        primary_intent=IntentKind.UNSUPPORTED,
        entities=entities,
        specialist_plan=(),
        discovery_required=False,
        clarification_reason=_UNSUPPORTED_REASON,
    )


def _match_intent(normalized_query: str) -> IntentKind:
    if _contains_any(normalized_query, _ITINERARY_SIGNALS):
        return IntentKind.ITINERARY_DRAFTING
    if _contains_any(normalized_query, _CULTURE_SIGNALS):
        return IntentKind.LOCAL_CULTURE
    if _contains_any(normalized_query, _NEARBY_SIGNALS):
        return IntentKind.NEARBY_DISCOVERY
    if _contains_any(normalized_query, _POI_DIRECT_SIGNALS) or (
        _contains_any(normalized_query, _POI_INFORMATION_SIGNALS)
        and _contains_any(normalized_query, _TRAVEL_CONTEXT_SIGNALS)
    ):
        return IntentKind.POI_INFORMATION
    if _contains_any(normalized_query, _GENERAL_TRAVEL_SIGNALS):
        return IntentKind.GENERAL_TRAVEL_HELP
    return IntentKind.UNSUPPORTED


def _extract_city(normalized_query: str) -> SupportedCity | None:
    hcmc_present = _contains_any(normalized_query, _HCMC_ALIASES)
    bangkok_present = _contains_any(normalized_query, _BANGKOK_ALIASES)
    if hcmc_present is bangkok_present:
        return None
    return SupportedCity.HCMC if hcmc_present else SupportedCity.BANGKOK


def _contains_any(value: str, phrases: tuple[str, ...]) -> bool:
    padded = f" {value} "
    return any(f" {phrase} " in padded for phrase in phrases)


def _normalize_for_matching(value: str) -> str:
    compatibility_normalized = unicodedata.normalize("NFKC", value)
    casefolded = compatibility_normalized.casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", casefolded)
    without_diacritics = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    words_only = "".join(
        " "
        if unicodedata.category(character).startswith(("P", "S"))
        else character
        for character in without_diacritics
    )
    return _WHITESPACE.sub(" ", words_only).strip()
