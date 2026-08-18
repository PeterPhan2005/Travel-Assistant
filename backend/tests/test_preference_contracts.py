"""Unit tests for the taxonomy-neutral preference contract."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from app.preferences.contracts import (
    MAX_ARRAY_ITEMS,
    MAX_CONTAINER_DEPTH,
    MAX_INTEGER_ABSOLUTE_VALUE,
    MAX_KEY_LENGTH,
    MAX_OBJECT_ITEMS,
    MAX_STRING_LENGTH,
    AgentPreferenceProjectionV1,
    BudgetPreference,
    PreferenceDocument,
    TravelInterest,
    TravelPace,
    TravelPreferenceDocument,
    project_for_agents,
)


def _document(preferences: object) -> PreferenceDocument:
    return PreferenceDocument.model_validate(
        {"schema_version": 1, "preferences": preferences}
    )


def test_contract_preserves_unicode_and_normalizes_object_order() -> None:
    document = _document(
        {
            "z": ["Tiếng Việt", None, True, 42],
            "a": {"địa_điểm": "Thành phố Hồ Chí Minh"},
        }
    )

    assert list(document.preferences) == ["a", "z"]
    assert document.preferences["a"] == {
        "địa_điểm": "Thành phố Hồ Chí Minh"
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": 2, "preferences": {}},
        {"schema_version": 1, "preferences": {}, "metadata": {}},
        {"schema_version": 1, "preferences": []},
        {"schema_version": 1, "preferences": {"number": 1.5}},
        {
            "schema_version": 1,
            "preferences": {
                "number": MAX_INTEGER_ABSOLUTE_VALUE + 1,
            },
        },
        {
            "schema_version": 1,
            "preferences": {"text": "x" * (MAX_STRING_LENGTH + 1)},
        },
        {
            "schema_version": 1,
            "preferences": {"x" * (MAX_KEY_LENGTH + 1): None},
        },
        {
            "schema_version": 1,
            "preferences": {"items": [None] * (MAX_ARRAY_ITEMS + 1)},
        },
        {
            "schema_version": 1,
            "preferences": {
                f"k{index}": None
                for index in range(MAX_OBJECT_ITEMS + 1)
            },
        },
        {"schema_version": 1, "preferences": {"tuple": (1, 2)}},
        {"schema_version": 1, "preferences": {"binary": b"secret"}},
        {"schema_version": 1, "preferences": {"custom": object()}},
    ],
)
def test_contract_rejects_unsupported_or_oversized_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PreferenceDocument.model_validate(payload)


def test_contract_rejects_excessive_nesting() -> None:
    nested: dict[str, object] = {}
    current = nested
    for _ in range(MAX_CONTAINER_DEPTH + 2):
        child: dict[str, object] = {}
        current["next"] = child
        current = child

    with pytest.raises(ValidationError):
        _document(nested)


def test_typed_travel_contract_is_closed_canonical_and_projectable() -> None:
    document = TravelPreferenceDocument.model_validate(
        {
            "schema_version": 2,
            "preferences": {
                "interests": ["nature_and_outdoors", "food_and_cafes"],
                "pace": "balanced",
                "budget_preference": "moderate",
            },
        }
    )

    assert document.preferences.interests == (
        TravelInterest.FOOD_AND_CAFES,
        TravelInterest.NATURE_AND_OUTDOORS,
    )
    assert project_for_agents(document) == AgentPreferenceProjectionV1(
        interests=document.preferences.interests,
        pace=TravelPace.BALANCED,
        budget_preference=BudgetPreference.MODERATE,
    )
    assert project_for_agents(PreferenceDocument.empty()) is None
    assert project_for_agents(TravelPreferenceDocument.empty()) is None


@pytest.mark.parametrize(
    "preferences",
    [
        {"interests": [], "pace": None},
        {
            "interests": [],
            "pace": None,
            "budget_preference": None,
            "inferred_trait": "hidden",
        },
        {
            "interests": ["food_and_cafes", "food_and_cafes"],
            "pace": None,
            "budget_preference": None,
        },
        {
            "interests": [
                "food_and_cafes",
                "culture_and_history",
                "scenic_and_landmarks",
                "nature_and_outdoors",
                "local_life_and_markets",
                "family_activities",
            ],
            "pace": None,
            "budget_preference": None,
        },
        {
            "interests": ["religion"],
            "pace": None,
            "budget_preference": None,
        },
    ],
)
def test_typed_travel_contract_rejects_partial_hidden_or_invalid_values(
    preferences: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        TravelPreferenceDocument.model_validate(
            {"schema_version": 2, "preferences": preferences}
        )
