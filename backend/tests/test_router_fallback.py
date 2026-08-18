"""Deterministic intent, plan, and entity tests for the Router fallback."""

from __future__ import annotations

import pytest

from app.agents.contracts import (
    IntentKind,
    RouterOutput,
    RouterRequest,
    SpecialistKind,
    SupportedCity,
)
from app.agents.router import match_router_fallback


def _request(
    query: str,
    *,
    city: SupportedCity | None = None,
    locale: str = "vi-VN",
) -> RouterRequest:
    return RouterRequest(
        user_query=query,
        locale=locale,
        city=city,
    )


@pytest.mark.parametrize(
    ("query", "intent"),
    [
        ("Lên lịch trình tham quan Sài Gòn", IntentKind.ITINERARY_DRAFTING),
        ("len lich trinh tham quan sai gon", IntentKind.ITINERARY_DRAFTING),
        ("Build a half-day travel plan", IntentKind.ITINERARY_DRAFTING),
        ("Văn hóa địa phương có gì cần lưu ý?", IntentKind.LOCAL_CULTURE),
        ("van hoa dia phuong co gi can luu y?", IntentKind.LOCAL_CULTURE),
        ("What local etiquette should I follow?", IntentKind.LOCAL_CULTURE),
        ("Tìm quán ăn gần tôi", IntentKind.NEARBY_DISCOVERY),
        ("tim quan an gan toi", IntentKind.NEARBY_DISCOVERY),
        ("Show places close by", IntentKind.NEARBY_DISCOVERY),
        ("Giới thiệu chợ Bến Thành", IntentKind.POI_INFORMATION),
        ("gioi thieu cho ben thanh", IntentKind.POI_INFORMATION),
        ("Tell me about the Grand Palace", IntentKind.POI_INFORMATION),
        ("Tôi cần hỗ trợ du lịch", IntentKind.GENERAL_TRAVEL_HELP),
        ("toi can ho tro du lich", IntentKind.GENERAL_TRAVEL_HELP),
        ("Help with my travel", IntentKind.GENERAL_TRAVEL_HELP),
        ("Viết mã Python giúp tôi", IntentKind.UNSUPPORTED),
        ("viet ma python giup toi", IntentKind.UNSUPPORTED),
        ("Explain binary search", IntentKind.UNSUPPORTED),
    ],
)
def test_fallback_covers_all_intents_in_vietnamese_and_english(
    query: str,
    intent: IntentKind,
) -> None:
    output = match_router_fallback(_request(query))

    assert output.primary_intent is intent
    assert RouterOutput.model_validate(output.model_dump()) == output


@pytest.mark.parametrize(
    ("intent", "plan", "discovery_required"),
    [
        (
            IntentKind.NEARBY_DISCOVERY,
            (SpecialistKind.DISCOVERY,),
            True,
        ),
        (
            IntentKind.POI_INFORMATION,
            (SpecialistKind.NARRATION,),
            False,
        ),
        (
            IntentKind.LOCAL_CULTURE,
            (SpecialistKind.LOCAL_CULTURE,),
            False,
        ),
        (
            IntentKind.ITINERARY_DRAFTING,
            (SpecialistKind.DISCOVERY, SpecialistKind.ITINERARY),
            True,
        ),
        (IntentKind.GENERAL_TRAVEL_HELP, (), False),
        (IntentKind.UNSUPPORTED, (), False),
    ],
)
def test_fallback_returns_only_canonical_plans(
    intent: IntentKind,
    plan: tuple[SpecialistKind, ...],
    discovery_required: bool,
) -> None:
    queries = {
        IntentKind.NEARBY_DISCOVERY: "địa điểm gần đây",
        IntentKind.POI_INFORMATION: "thông tin về địa điểm này",
        IntentKind.LOCAL_CULTURE: "phong tục địa phương",
        IntentKind.ITINERARY_DRAFTING: "kế hoạch tham quan một ngày",
        IntentKind.GENERAL_TRAVEL_HELP: "hỗ trợ chuyến đi",
        IntentKind.UNSUPPORTED: "cách sắp xếp một danh sách số",
    }

    output = match_router_fallback(_request(queries[intent]))

    assert output.primary_intent is intent
    assert output.specialist_plan == plan
    assert output.discovery_required is discovery_required
    assert (output.clarification_reason is not None) is (
        intent is IntentKind.UNSUPPORTED
    )


def test_matching_is_case_whitespace_diacritic_and_punctuation_insensitive() -> None:
    variants = (
        "  ĐỊA   ĐIỂM   GẦN   TÔI  ",
        "dia diem gan toi",
        "\tPlaces—Close   By!\n",
    )

    outputs = tuple(match_router_fallback(_request(value)) for value in variants)

    assert all(
        output.primary_intent is IntentKind.NEARBY_DISCOVERY
        for output in outputs
    )


def test_repeated_matching_is_deterministic_and_does_not_mutate_request() -> None:
    request = _request(
        "Lên kế hoạch tham quan Bangkok",
    )
    original_json = request.model_dump_json()

    outputs = tuple(match_router_fallback(request) for _ in range(10))

    assert all(output == outputs[0] for output in outputs)
    assert request.model_dump_json() == original_json


def test_documented_intent_precedence_resolves_multiple_signals() -> None:
    output = match_router_fallback(
        _request(
            "Lên lịch trình để tìm địa điểm gần đây và học văn hóa địa phương"
        )
    )

    assert output.primary_intent is IntentKind.ITINERARY_DRAFTING


@pytest.mark.parametrize(
    ("query", "expected_city"),
    [
        ("du lịch HCMC", SupportedCity.HCMC),
        ("du lịch Ho Chi Minh City", SupportedCity.HCMC),
        ("du lịch Hồ Chí Minh", SupportedCity.HCMC),
        ("du lịch Thành phố Hồ Chí Minh", SupportedCity.HCMC),
        ("du lịch Sài Gòn", SupportedCity.HCMC),
        ("travel to Saigon", SupportedCity.HCMC),
        ("du lịch Bangkok", SupportedCity.BANGKOK),
        ("du lịch Băng Cốc", SupportedCity.BANGKOK),
    ],
)
def test_accepted_city_aliases_normalize_conservatively(
    query: str,
    expected_city: SupportedCity,
) -> None:
    output = match_router_fallback(_request(query))

    assert output.entities.city is expected_city


def test_explicit_city_is_preserved_and_wins_over_query_city() -> None:
    request = _request(
        "Lên kế hoạch tham quan Bangkok",
        city=SupportedCity.HCMC,
    )

    output = match_router_fallback(request)

    assert output.entities.city is SupportedCity.HCMC
    assert request.city is SupportedCity.HCMC


def test_conflicting_query_cities_do_not_force_an_entity() -> None:
    output = match_router_fallback(
        _request("So sánh chuyến đi Bangkok và Sài Gòn")
    )

    assert output.entities.city is None


def test_locale_does_not_imply_city_or_other_entities() -> None:
    output = match_router_fallback(
        _request(
            "Tôi cần hỗ trợ chuyến đi",
            locale="th-TH",
        )
    )

    assert output.entities.city is None
    assert output.entities.category is None
    assert output.entities.query_term is None
    assert output.entities.referenced_poi_ids == ()
    assert output.entities.itinerary_constraints is None


@pytest.mark.parametrize(
    "query",
    [
        "Please plan my study schedule",
        "Information about Python decorators",
        "What is dependency injection?",
    ],
)
def test_isolated_generic_words_do_not_create_travel_intents(
    query: str,
) -> None:
    output = match_router_fallback(_request(query))

    assert output.primary_intent is IntentKind.UNSUPPORTED
    assert output.clarification_reason
