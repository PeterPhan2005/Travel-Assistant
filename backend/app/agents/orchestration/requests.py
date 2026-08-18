"""Pure scoped request construction for each independent service boundary."""

from __future__ import annotations

from collections.abc import Iterable

from app.agents.contracts import (
    AgentRuntimeRequest,
    DiscoveryCandidate,
    DiscoveryOutput,
    DiscoveryRequest,
    EvidenceBundle,
    FactKind,
    IntentKind,
    ItineraryConstraints,
    ItineraryRequest,
    LocalCultureRequest,
    NarrationRequest,
    PoiIdentity,
    RouterOutput,
    RouterRequest,
    SpecialistKind,
    SupportedCity,
)
from app.agents.orchestration.evidence import (
    filter_culture_evidence,
    filter_poi_evidence,
)
from app.agents.orchestration.policy import OrchestrationPolicy

_DISCOVERY_FACT_KINDS = frozenset(
    {
        FactKind.CATEGORY,
        FactKind.DISTANCE,
        FactKind.IDENTITY,
        FactKind.LOCATION,
        FactKind.OPENING_HOURS,
        FactKind.PRICE,
        FactKind.RATING,
    }
)
_SPECIALIST_FACT_KINDS = {
    SpecialistKind.NARRATION: frozenset(
        {
            FactKind.DESCRIPTION,
            FactKind.HISTORY,
        }
    ),
    SpecialistKind.LOCAL_CULTURE: frozenset(
        {
            FactKind.CULTURE,
            FactKind.ETIQUETTE,
        }
    ),
    SpecialistKind.ITINERARY: frozenset(
        {
            FactKind.ITINERARY_CONSTRAINT,
        }
    ),
}


def build_router_request(request: AgentRuntimeRequest) -> RouterRequest:
    """Map only query routing fields; preferences never reach the Router."""
    return RouterRequest(
        user_query=request.user_query,
        locale=request.locale,
        city=request.city,
    )


def resolve_city(
    request: AgentRuntimeRequest,
    router: RouterOutput,
) -> SupportedCity | None:
    """Prefer the Router's typed city without inferring one from prose."""
    return router.entities.city or request.city


def build_discovery_request(
    request: AgentRuntimeRequest,
    router: RouterOutput,
    policy: OrchestrationPolicy,
) -> DiscoveryRequest:
    """Map exact origin, policy limits, router filters, and fact needs."""
    city = resolve_city(request, router)
    if city is None or request.discovery_origin is None:
        raise ValueError("Discovery requires explicit city and origin.")
    facts = set(_DISCOVERY_FACT_KINDS)
    for specialist in router.specialist_plan:
        facts.update(_SPECIALIST_FACT_KINDS.get(specialist, ()))
    return DiscoveryRequest(
        city=city,
        origin=request.discovery_origin,
        radius_metres=policy.discovery_radius_metres,
        limit=policy.discovery_limit,
        query=router.entities.query_term,
        category=router.entities.category,
        requested_fact_kinds=tuple(sorted(facts, key=lambda item: item.value)),
    )


def merge_candidates(
    groups: Iterable[tuple[DiscoveryCandidate, ...]],
) -> tuple[DiscoveryCandidate, ...]:
    """Preserve first-seen order and reject conflicting duplicate identities."""
    candidates: list[DiscoveryCandidate] = []
    by_id: dict[str, DiscoveryCandidate] = {}
    for group in groups:
        for candidate in group:
            existing = by_id.setdefault(candidate.id, candidate)
            if existing != candidate:
                raise ValueError("Conflicting candidate identity.")
            if candidate not in candidates:
                candidates.append(candidate)
    return tuple(candidates)


def candidate_identity(candidate: DiscoveryCandidate) -> PoiIdentity:
    """Copy exact candidate identity fields without correction."""
    return PoiIdentity(
        poi_id=candidate.id,
        canonical_name=candidate.canonical_name,
        city=candidate.city,
        category=candidate.category,
    )


def build_narration_request(
    request: AgentRuntimeRequest,
    router: RouterOutput,
    discovery: DiscoveryOutput | None,
    evidence: EvidenceBundle,
    policy: OrchestrationPolicy,
) -> NarrationRequest:
    """Select only an explicit or documented deterministic POI target."""
    discovered = discovery.candidates if discovery is not None else ()
    candidates = merge_candidates((discovered, request.context.candidates))
    selected = request.context.selected_poi
    if selected is None:
        by_id = {candidate.id: candidate for candidate in candidates}
        selected_candidate = next(
            (
                by_id[poi_id]
                for poi_id in router.entities.referenced_poi_ids
                if poi_id in by_id
            ),
            None,
        )
        if selected_candidate is not None:
            selected = candidate_identity(selected_candidate)
        elif (
            router.primary_intent is IntentKind.POI_INFORMATION
            and SpecialistKind.DISCOVERY in router.specialist_plan
            and discovery is not None
            and discovery.candidates
        ):
            selected = candidate_identity(discovery.candidates[0])
    if selected is None:
        raise ValueError("Narration requires an explicit POI target.")
    resolved_city = resolve_city(request, router)
    if resolved_city is not None and selected.city is not resolved_city:
        raise ValueError("Narration POI conflicts with the resolved city.")
    return NarrationRequest(
        poi=selected,
        evidence=filter_poi_evidence(evidence, selected.poi_id),
        locale=request.locale,
        word_range=policy.narration_word_range,
    )


def build_local_culture_request(
    request: AgentRuntimeRequest,
    router: RouterOutput,
    evidence: EvidenceBundle,
) -> LocalCultureRequest:
    """Use one explicit bounded topic and culture-only evidence."""
    city = resolve_city(request, router)
    if city is None:
        raise ValueError("Local Culture requires an explicit city.")
    topic = router.entities.query_term or request.user_query
    return LocalCultureRequest(
        city=city,
        topic=topic,
        locale=request.locale,
        evidence=filter_culture_evidence(evidence),
    )


def build_itinerary_request(
    request: AgentRuntimeRequest,
    router: RouterOutput,
    discovery: DiscoveryOutput | None,
    evidence: EvidenceBundle,
    policy: OrchestrationPolicy,
) -> ItineraryRequest:
    """Map only explicit window, candidates, origin, and typed constraints."""
    city = resolve_city(request, router)
    window = request.context.itinerary_window
    if city is None or window is None:
        raise ValueError(
            "Itinerary requires explicit city and local window."
        )
    discovered = discovery.candidates if discovery is not None else ()
    candidates = merge_candidates((discovered, request.context.candidates))
    if not candidates:
        raise ValueError("Itinerary requires explicit candidates.")
    routed = router.entities.itinerary_constraints
    maximum_stops = (
        routed.maximum_stops
        if routed is not None and routed.maximum_stops is not None
        else policy.default_itinerary_maximum_stops
    )
    notes = routed.notes if routed is not None else ()
    preferred_categories = (
        (router.entities.category,)
        if router.entities.category is not None
        else ()
    )
    return ItineraryRequest(
        city=city,
        local_date=window.local_date,
        timezone=window.timezone,
        start_local_time=window.start_local_time,
        end_local_time=window.end_local_time,
        candidates=candidates,
        evidence=evidence,
        constraints=ItineraryConstraints(
            maximum_stops=maximum_stops,
            required_poi_ids=router.entities.referenced_poi_ids,
            excluded_poi_ids=(),
            preferred_categories=preferred_categories,
            notes=notes,
        ),
        start_origin=request.discovery_origin,
    )
