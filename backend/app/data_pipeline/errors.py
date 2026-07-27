"""Stable actionable error contract for curated validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationIssue:
    """One sanitized, machine-readable validation failure."""

    source_path: Path
    code: str
    entity_type: str
    record_id: str | None
    field_path: str
    message: str

    def sort_key(self) -> tuple[str, str, str, str, str]:
        """Return a total deterministic ordering."""
        return (
            self.source_path.as_posix(),
            self.entity_type,
            self.record_id or "",
            self.field_path,
            self.code,
        )

    def render(self) -> str:
        """Render one concise line without source documents or secrets."""
        record = self.record_id if self.record_id is not None else "-"
        return (
            f"{self.source_path}: code={self.code} "
            f"entity={self.entity_type} record={record} "
            f"field={self.field_path} message={self.message}"
        )
