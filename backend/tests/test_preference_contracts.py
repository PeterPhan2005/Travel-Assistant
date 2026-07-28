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
    PreferenceDocument,
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

