"""Shared strict values for provider-neutral agent contracts."""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictBool,
    StrictInt,
    model_validator,
)

from app.providers.poi.models import SupportedCity as SupportedCity

MAX_SOURCES = 100
MAX_CLAIMS = 200
MAX_REFERENCES = 100

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_LOCALE_PATTERN = r"^[a-z]{2,3}(?:-[A-Z]{2})?$"
_CURRENCY_PATTERN = r"^[A-Z]{3}$"
_SENSITIVE_MESSAGE_PATTERN = re.compile(
    r"(api[_ -]?key|authorization|bearer|database_url|firebase|"
    r"password|postgres(?:ql)?://|prompt|stack trace|token|uid)",
    re.IGNORECASE,
)


class ContractModel(BaseModel):
    """Immutable strict-by-type and strict-by-shape public contract base."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
        revalidate_instances="always",
    )


def _validate_identifier(value: str) -> str:
    if not value or not _IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError("Identifier contains unsupported characters.")
    if ".." in value or "/" in value or "\\" in value:
        raise ValueError("Identifier must not contain path traversal.")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError("Identifier must not contain control characters.")
    return value


def _validate_text(value: str) -> str:
    if not value:
        raise ValueError("Text must not be blank.")
    if any(
        unicodedata.category(character) == "Cc"
        and character not in {"\n", "\t"}
        for character in value
    ):
        raise ValueError("Text must not contain control characters.")
    return value


def _validate_plain_output(value: str) -> str:
    _validate_text(value)
    if "<" in value or ">" in value:
        raise ValueError("HTML-like output is not accepted.")
    if "```" in value or re.search(r"!?\[[^\]]+\]\([^)]+\)", value):
        raise ValueError("Rendered markdown payloads are not accepted.")
    return value


def _validate_safe_message(value: str) -> str:
    _validate_plain_output(value)
    if _SENSITIVE_MESSAGE_PATTERN.search(value):
        raise ValueError("Issue message contains an internal or sensitive term.")
    return value


RequestId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=128),
    AfterValidator(_validate_identifier),
]
PoiId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=280),
    AfterValidator(_validate_identifier),
]
SourceId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=120),
    AfterValidator(_validate_identifier),
]
EvidenceId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=120),
    AfterValidator(_validate_identifier),
]
ClaimId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=120),
    AfterValidator(_validate_identifier),
]
ItineraryItemId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=120),
    AfterValidator(_validate_identifier),
]
SpecialistOutputId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=120),
    AfterValidator(_validate_identifier),
]
GuidanceItemId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=120),
    AfterValidator(_validate_identifier),
]
LocaleCode = Annotated[
    str,
    Field(strict=True, min_length=2, max_length=16, pattern=_LOCALE_PATTERN),
]
NormalizedQuery = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=500),
    AfterValidator(_validate_text),
]
ShortText = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=200),
    AfterValidator(_validate_text),
]
MediumText = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=1000),
    AfterValidator(_validate_text),
]
PlainOutputText = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=6000),
    AfterValidator(_validate_plain_output),
]
PlainShortText = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=240),
    AfterValidator(_validate_plain_output),
]
SafeMessage = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=240),
    AfterValidator(_validate_safe_message),
]
CurrencyCode = Annotated[
    str,
    Field(
        strict=True,
        min_length=3,
        max_length=3,
        pattern=_CURRENCY_PATTERN,
    ),
]


class AgentKind(StrEnum):
    """Closed identity set for model-executed runtime agents."""

    ROUTER = "router"
    DISCOVERY = "discovery"
    NARRATION = "narration"
    LOCAL_CULTURE = "local_culture"
    ITINERARY = "itinerary"
    GROUNDING_REVIEWER = "grounding_reviewer"
    RESPONSE_COMPOSER = "response_composer"


class SpecialistKind(StrEnum):
    """Closed router fan-out set; review and composition are mandatory stages."""

    DISCOVERY = "discovery"
    NARRATION = "narration"
    LOCAL_CULTURE = "local_culture"
    ITINERARY = "itinerary"


class IntentKind(StrEnum):
    """Closed MVP intent taxonomy used by the router contract."""

    NEARBY_DISCOVERY = "nearby_discovery"
    POI_INFORMATION = "poi_information"
    LOCAL_CULTURE = "local_culture"
    ITINERARY_DRAFTING = "itinerary_drafting"
    GENERAL_TRAVEL_HELP = "general_travel_help"
    UNSUPPORTED = "unsupported"


class SourceType(StrEnum):
    """Approved provenance classes already accepted by curated data."""

    OFFICIAL_GOVERNMENT = "official_government"
    OFFICIAL_INSTITUTION = "official_institution"
    OFFICIAL_OPERATOR = "official_operator"
    OFFICIAL_TOURISM = "official_tourism"


class FactKind(StrEnum):
    """Closed factual-claim taxonomy for current product behavior."""

    IDENTITY = "identity"
    LOCATION = "location"
    CATEGORY = "category"
    DISTANCE = "distance"
    DESCRIPTION = "description"
    HISTORY = "history"
    CULTURE = "culture"
    MENU_ITEM = "menu_item"
    PRICE = "price"
    RATING = "rating"
    OPENING_HOURS = "opening_hours"
    ETIQUETTE = "etiquette"
    ITINERARY_CONSTRAINT = "itinerary_constraint"


class FailureCode(StrEnum):
    """Sanitized failure and warning codes shared by later orchestration."""

    INVALID_INPUT = "invalid_input"
    INVALID_OUTPUT = "invalid_output"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    SPECIALIST_TIMEOUT = "specialist_timeout"
    SPECIALIST_FAILED = "specialist_failed"
    GROUNDING_REJECTED = "grounding_rejected"
    PARTIAL_RESULT = "partial_result"
    UNSUPPORTED_INTENT = "unsupported_intent"
    LATENCY_BUDGET_EXCEEDED = "latency_budget_exceeded"
    INTERNAL = "internal"


class SourceRecord(ContractModel):
    """Bounded source metadata; timestamps must be timezone-aware."""

    source_id: SourceId
    source_type: SourceType
    label: ShortText
    publisher: ShortText | None = None
    url: HttpUrl | None = None
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime | None = None


class PriceFact(ContractModel):
    """Exact integer money value and source freshness for a price claim."""

    price_minor_units: Annotated[
        StrictInt,
        Field(ge=0, le=9_223_372_036_854_775_807),
    ]
    currency: CurrencyCode
    source_updated_at: AwareDatetime


class FactualClaim(ContractModel):
    """One factual statement closed over explicit supporting source IDs."""

    claim_id: ClaimId
    evidence_id: EvidenceId
    fact_kind: FactKind
    statement: MediumText
    supporting_source_ids: Annotated[
        tuple[SourceId, ...],
        Field(min_length=1, max_length=MAX_REFERENCES),
    ]
    poi_id: PoiId | None = None
    freshness_at: AwareDatetime | None = None
    price: PriceFact | None = None

    @model_validator(mode="after")
    def validate_fact_shape(self) -> FactualClaim:
        """Enforce source uniqueness and price-specific typed data."""
        if self.supporting_source_ids != tuple(
            sorted(set(self.supporting_source_ids))
        ):
            raise ValueError("Supporting source IDs must be unique and sorted.")
        if self.fact_kind is FactKind.PRICE:
            if self.price is None:
                raise ValueError("Price claims require exact typed price data.")
            if self.freshness_at != self.price.source_updated_at:
                raise ValueError(
                    "Price freshness must equal its source update timestamp."
                )
        elif self.price is not None:
            raise ValueError("Only price claims may contain price data.")
        return self


class EvidenceBundle(ContractModel):
    """Bounded source/claim registry with complete local reference closure."""

    sources: Annotated[
        tuple[SourceRecord, ...],
        Field(max_length=MAX_SOURCES),
    ] = ()
    claims: Annotated[
        tuple[FactualClaim, ...],
        Field(max_length=MAX_CLAIMS),
    ] = ()

    @model_validator(mode="after")
    def validate_registry(self) -> EvidenceBundle:
        """Reject duplicate, unsorted, or missing source/claim references."""
        source_ids = tuple(source.source_id for source in self.sources)
        claim_ids = tuple(claim.claim_id for claim in self.claims)
        evidence_ids = tuple(claim.evidence_id for claim in self.claims)
        if source_ids != tuple(sorted(set(source_ids))):
            raise ValueError("Sources must be unique and sorted by source ID.")
        if claim_ids != tuple(sorted(set(claim_ids))):
            raise ValueError("Claims must be unique and sorted by claim ID.")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence IDs must be unique.")
        known_sources = set(source_ids)
        for claim in self.claims:
            if not set(claim.supporting_source_ids).issubset(known_sources):
                raise ValueError("Claim references a missing source.")
        return self

    @property
    def source_ids(self) -> frozenset[str]:
        """Return source identities for deterministic cross-contract checks."""
        return frozenset(source.source_id for source in self.sources)

    @property
    def claim_ids(self) -> frozenset[str]:
        """Return claim identities for deterministic cross-contract checks."""
        return frozenset(claim.claim_id for claim in self.claims)


class PoiIdentity(ContractModel):
    """Minimal provider-neutral POI identity passed to specialists."""

    poi_id: PoiId
    canonical_name: ShortText
    city: SupportedCity
    category: ShortText


class AgentWarning(ContractModel):
    """Safe recoverable warning with no provider or exception payload."""

    stage: AgentKind
    code: FailureCode
    message: SafeMessage
    retryable: StrictBool


class AgentFailure(ContractModel):
    """Safe failed-stage record with no exception, prompt, or credentials."""

    stage: AgentKind
    code: FailureCode
    message: SafeMessage
    retryable: StrictBool


def validate_sorted_unique(
    values: tuple[str, ...],
    *,
    label: str,
) -> None:
    """Require deterministic ascending unique string identities."""
    if values != tuple(sorted(set(values))):
        raise ValueError(f"{label} must be unique and sorted.")


def validate_references(
    *,
    used_claim_ids: tuple[str, ...],
    used_source_ids: tuple[str, ...],
    evidence: EvidenceBundle,
) -> None:
    """Close used claim/source IDs over one validated evidence bundle."""
    validate_sorted_unique(used_claim_ids, label="Used claim IDs")
    validate_sorted_unique(used_source_ids, label="Used source IDs")
    if not set(used_claim_ids).issubset(evidence.claim_ids):
        raise ValueError("Output references an unknown claim.")
    if not set(used_source_ids).issubset(evidence.source_ids):
        raise ValueError("Output references an unknown source.")
    claims_by_id = {
        claim.claim_id: claim
        for claim in evidence.claims
    }
    supported_sources = {
        source_id
        for claim_id in used_claim_ids
        for source_id in claims_by_id[claim_id].supporting_source_ids
    }
    if not set(used_source_ids).issubset(supported_sources):
        raise ValueError("Used source is not attached to a used claim.")


def validate_issue_stage(
    issue: AgentWarning | AgentFailure,
    expected: AgentKind,
) -> None:
    """Require a stage outcome to carry only issues for its own agent."""
    if issue.stage is not expected:
        raise ValueError("Issue stage does not match the stage outcome.")
