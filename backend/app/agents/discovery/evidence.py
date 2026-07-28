"""Pure deterministic evidence assembly and model-output closure."""

from __future__ import annotations

from hashlib import sha256

from pydantic import ValidationError

from app.agents.contracts import (
    AgentFailure,
    AgentKind,
    DiscoveryCandidate,
    DiscoveryCompleteness,
    DiscoveryOutput,
    DiscoveryRequest,
    EvidenceBundle,
    FactKind,
    FactualClaim,
    FailureCode,
    PriceFact,
    SourceRecord,
)
from app.agents.discovery.errors import (
    DiscoveryExecutionError,
    InvalidDiscoveryModelOutputError,
)
from app.agents.discovery.models import (
    DiscoveryRegistrySnapshot,
    MenuItemResult,
    PoiToolCandidate,
    ToolSource,
)
from app.providers.poi.models import Coordinates, SourceReference


def assemble_discovery_output(
    request: DiscoveryRequest,
    snapshot: DiscoveryRegistrySnapshot,
) -> DiscoveryOutput:
    """Convert one immutable registry into the only public result."""
    if snapshot.poi_result is None:
        failure = (
            snapshot.failures[0]
            if snapshot.failures
            else _invalid_registry_failure()
        )
        raise DiscoveryExecutionError(failure)

    candidates = tuple(
        _candidate_from_tool(item) for item in snapshot.poi_result.items
    )
    evidence = _assemble_evidence(request, snapshot)
    has_partial_issue = bool(snapshot.failures) or not snapshot.poi_result.is_complete
    completeness = (
        DiscoveryCompleteness.PARTIAL
        if candidates and has_partial_issue
        else DiscoveryCompleteness.COMPLETE
    )
    if not candidates and snapshot.failures:
        raise DiscoveryExecutionError(snapshot.failures[0])
    try:
        return DiscoveryOutput(
            candidates=candidates,
            evidence=evidence,
            provider_failures=snapshot.failures,
            completeness=completeness,
            is_truncated=not snapshot.poi_result.is_complete,
        )
    except (TypeError, ValueError, ValidationError):
        raise DiscoveryExecutionError(_invalid_registry_failure()) from None


def validate_output_closure(
    output: object,
    expected: DiscoveryOutput,
) -> DiscoveryOutput:
    """Require byte-equivalent facts, order, failures, and completeness."""
    if not isinstance(output, DiscoveryOutput):
        raise InvalidDiscoveryModelOutputError
    try:
        validated = DiscoveryOutput.model_validate(
            output.model_dump(mode="python")
        )
    except (TypeError, ValueError, ValidationError):
        raise InvalidDiscoveryModelOutputError from None
    if validated != expected:
        raise InvalidDiscoveryModelOutputError
    return validated


def _assemble_evidence(
    request: DiscoveryRequest,
    snapshot: DiscoveryRegistrySnapshot,
) -> EvidenceBundle:
    if snapshot.poi_result is None:
        raise DiscoveryExecutionError(_invalid_registry_failure())
    sources: dict[str, SourceRecord] = {}
    claims: list[FactualClaim] = []
    requested = frozenset(request.requested_fact_kinds)

    for candidate in snapshot.poi_result.items:
        candidate_source_ids = _add_sources(sources, candidate.sources)
        if not candidate_source_ids:
            continue
        if FactKind.IDENTITY in requested:
            claims.append(
                _claim(
                    candidate,
                    FactKind.IDENTITY,
                    f"{candidate.canonical_name} is a point of interest "
                    f"in {candidate.city.value}.",
                    candidate_source_ids,
                )
            )
        if FactKind.CATEGORY in requested:
            claims.append(
                _claim(
                    candidate,
                    FactKind.CATEGORY,
                    f"{candidate.canonical_name} has category "
                    f"{candidate.category}.",
                    candidate_source_ids,
                )
            )
        if FactKind.LOCATION in requested and candidate.address is not None:
            claims.append(
                _claim(
                    candidate,
                    FactKind.LOCATION,
                    f"{candidate.canonical_name} is at {candidate.address}.",
                    candidate_source_ids,
                )
            )
        if FactKind.RATING in requested and candidate.rating is not None:
            claims.append(
                _claim(
                    candidate,
                    FactKind.RATING,
                    f"{candidate.canonical_name} has rating "
                    f"{format(candidate.rating, 'f')}.",
                    candidate_source_ids,
                )
            )
        if (
            FactKind.OPENING_HOURS in requested
            and candidate.opening_hours_summary is not None
        ):
            claims.append(
                _claim(
                    candidate,
                    FactKind.OPENING_HOURS,
                    f"{candidate.canonical_name} opening hours are "
                    f"{candidate.opening_hours_summary}.",
                    candidate_source_ids,
                )
            )

    candidates_by_provider_id = {
        candidate.provider_id: candidate
        for candidate in snapshot.poi_result.items
    }
    if snapshot.menu_result is not None:
        for item in snapshot.menu_result.items:
            selected_candidate = candidates_by_provider_id.get(
                item.poi_provider_id
            )
            if selected_candidate is None:
                raise DiscoveryExecutionError(_invalid_registry_failure())
            source_ids = _add_sources(sources, (item.source,))
            claims.extend(
                _menu_claims(
                    requested,
                    selected_candidate,
                    item,
                    source_ids,
                )
            )

    try:
        return EvidenceBundle(
            sources=tuple(sources[source_id] for source_id in sorted(sources)),
            claims=tuple(sorted(claims, key=lambda claim: claim.claim_id)),
        )
    except (TypeError, ValueError, ValidationError):
        raise DiscoveryExecutionError(_invalid_registry_failure()) from None


def _candidate_from_tool(item: PoiToolCandidate) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        id=item.id,
        provider=item.provider,
        provider_id=item.provider_id,
        canonical_name=item.canonical_name,
        city=item.city,
        category=item.category,
        address=item.address,
        coordinates=Coordinates(
            latitude=item.coordinates.latitude,
            longitude=item.coordinates.longitude,
        ),
        distance_metres=item.distance_metres,
        rating=item.rating,
        rating_count=item.rating_count,
        price_level=item.price_level,
        opening_hours_summary=item.opening_hours_summary,
        sources=tuple(
            SourceReference(
                source_id=source.source_id,
                source_type=source.source_type.value,
                label=source.label,
                publisher=source.publisher,
                url=source.url,
                published_at=source.published_at,
                retrieved_at=source.retrieved_at,
            )
            for source in item.sources
        ),
        retrieved_at=item.retrieved_at,
        is_curated=item.is_curated,
        is_externally_supplied=item.is_externally_supplied,
    )


def _add_sources(
    registry: dict[str, SourceRecord],
    tool_sources: tuple[ToolSource, ...],
) -> tuple[str, ...]:
    source_ids: list[str] = []
    for source in tool_sources:
        record = SourceRecord(
            source_id=source.source_id,
            source_type=source.source_type,
            label=source.label,
            publisher=source.publisher,
            url=source.url,
            published_at=source.published_at,
            retrieved_at=source.retrieved_at,
        )
        existing = registry.setdefault(record.source_id, record)
        if existing != record:
            raise DiscoveryExecutionError(_invalid_registry_failure())
        source_ids.append(record.source_id)
    return tuple(sorted(source_ids))


def _claim(
    candidate: PoiToolCandidate,
    fact_kind: FactKind,
    statement: str,
    source_ids: tuple[str, ...],
) -> FactualClaim:
    identity = f"{candidate.id}|{fact_kind.value}"
    return FactualClaim(
        claim_id=_stable_id("claim", identity),
        evidence_id=_stable_id("evidence", identity),
        fact_kind=fact_kind,
        statement=statement,
        supporting_source_ids=source_ids,
        poi_id=candidate.id,
        freshness_at=candidate.retrieved_at,
    )


def _menu_claims(
    requested: frozenset[FactKind],
    candidate: PoiToolCandidate,
    item: MenuItemResult,
    source_ids: tuple[str, ...],
) -> list[FactualClaim]:
    claims: list[FactualClaim] = []
    identity = f"{candidate.id}|{item.menu_item_id}"
    if FactKind.MENU_ITEM in requested:
        claims.append(
            FactualClaim(
                claim_id=_stable_id(
                    "claim",
                    f"{identity}|{FactKind.MENU_ITEM.value}",
                ),
                evidence_id=_stable_id(
                    "evidence",
                    f"{identity}|{FactKind.MENU_ITEM.value}",
                ),
                fact_kind=FactKind.MENU_ITEM,
                statement=f"{item.item_name} is listed for "
                f"{candidate.canonical_name}.",
                supporting_source_ids=source_ids,
                poi_id=candidate.id,
                freshness_at=item.source_updated_at,
            )
        )
    if FactKind.PRICE in requested:
        claims.append(
            FactualClaim(
                claim_id=_stable_id(
                    "claim",
                    f"{identity}|{FactKind.PRICE.value}",
                ),
                evidence_id=_stable_id(
                    "evidence",
                    f"{identity}|{FactKind.PRICE.value}",
                ),
                fact_kind=FactKind.PRICE,
                statement=f"{item.item_name} is listed at "
                f"{item.price_minor_units} {item.currency}.",
                supporting_source_ids=source_ids,
                poi_id=candidate.id,
                freshness_at=item.source_updated_at,
                price=PriceFact(
                    price_minor_units=item.price_minor_units,
                    currency=item.currency,
                    source_updated_at=item.source_updated_at,
                ),
            )
        )
    return claims


def _stable_id(kind: str, identity: str) -> str:
    digest = sha256(identity.encode("utf-8")).hexdigest()[:32]
    return f"discovery:{kind}:{digest}"


def _invalid_registry_failure() -> AgentFailure:
    return AgentFailure(
        stage=AgentKind.DISCOVERY,
        code=FailureCode.INVALID_OUTPUT,
        message="Discovery data could not be validated.",
        retryable=False,
    )
