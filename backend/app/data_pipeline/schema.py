"""Deterministic JSON Schema generation and drift checking."""

from __future__ import annotations

import json

from app.data_pipeline.models import CuratedPackageV1
from app.data_pipeline.paths import CURATED_SCHEMA_PATH

SCHEMA_ID = (
    "https://travel-assistant.invalid/schemas/"
    "curated-package-v1.schema.json"
)


def generated_schema_text() -> str:
    """Return the canonical committed schema bytes as UTF-8 text."""
    schema = CuratedPackageV1.model_json_schema(
        mode="validation",
        ref_template="#/$defs/{model}",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = SCHEMA_ID
    return json.dumps(
        schema,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_schema() -> None:
    """Regenerate the versioned schema from Pydantic."""
    CURATED_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    CURATED_SCHEMA_PATH.write_text(
        generated_schema_text(),
        encoding="utf-8",
    )


def schema_is_current() -> bool:
    """Return whether the committed schema exactly matches generation."""
    try:
        committed = CURATED_SCHEMA_PATH.read_text(encoding="utf-8")
    except OSError:
        return False
    return committed == generated_schema_text()
