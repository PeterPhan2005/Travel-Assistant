"""JSON Schema generation, alignment, and accepted-package tests."""

from __future__ import annotations

import json

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from app.data_pipeline.loader import load_all_packages
from app.data_pipeline.paths import CURATED_SCHEMA_PATH
from app.data_pipeline.schema import generated_schema_text, schema_is_current


def test_committed_schema_is_current_and_valid_draft_2020_12() -> None:
    schema = json.loads(
        CURATED_SCHEMA_PATH.read_text(encoding="utf-8")
    )

    assert schema_is_current()
    assert CURATED_SCHEMA_PATH.read_text(encoding="utf-8") == (
        generated_schema_text()
    )
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == (
        "https://json-schema.org/draft/2020-12/schema"
    )
    assert schema["properties"]["schema_version"]["const"] == 1


def test_committed_packages_validate_with_json_schema_and_pydantic() -> None:
    schema = json.loads(
        CURATED_SCHEMA_PATH.read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    result = load_all_packages()

    assert result.is_valid
    for loaded in result.packages:
        raw = yaml.safe_load(
            loaded.source_path.read_text(encoding="utf-8")
        )
        assert list(validator.iter_errors(raw)) == []
        assert loaded.package.schema_version == 1
