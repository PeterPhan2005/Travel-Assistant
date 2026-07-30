"""T049 privacy-safe tracing, usage, context, and store tests."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import traceback
from collections.abc import Callable, Coroutine
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from agents import RunConfig
from agents.usage import Usage
from openai.types.responses.response_usage import (
    InputTokensDetails,
    OutputTokensDetails,
)
from pydantic import SecretStr, ValidationError

from app.agents.contracts import (
    AgentKind,
    FailureCode,
    RuntimeResultStatus,
    StageStatus,
)
from app.agents.observability import (
    AgentObservabilityConflictError,
    AgentObservabilityPolicy,
    AgentObservabilityQueryError,
    AgentObservabilityService,
    AgentObservabilityStoreError,
    AgentRequestTraceQuery,
    AgentStageObservation,
    AgentTokenUsage,
    AgentTraceQuery,
    AgentTraceRecord,
    AgentUsageQuery,
    InMemoryAgentObservabilityStore,
)
from app.agents.observability.context import (
    bind_request_observation,
    capture_usage_for_current_attempt,
    current_observation_identity,
    observation_attempt,
)
from app.agents.observability.store import AgentObservabilityStore
from app.agents.observability.sdk import (
    ATTEMPT_SPAN_NAME,
    WORKFLOW_NAME,
    AgentUsageAdaptationError,
    capture_sdk_result_usage,
    run_config_for_observation,
    sdk_attempt_span,
    start_workflow_trace,
    token_usage_from_sdk,
)

BACKEND = Path(__file__).resolve().parents[1]
TRACE_A = "trace_00000000000000000000000000000001"
TRACE_B = "trace_00000000000000000000000000000002"
REQUEST_A = "request-observation-a"
SDK_ADAPTER_CASES = (
    ("router", AgentKind.ROUTER),
    ("discovery", AgentKind.DISCOVERY),
    ("narration", AgentKind.NARRATION),
    ("local_culture", AgentKind.LOCAL_CULTURE),
    ("itinerary", AgentKind.ITINERARY),
    ("grounding", AgentKind.GROUNDING_REVIEWER),
    ("composer", AgentKind.RESPONSE_COMPOSER),
)


def _run_async_test(
    test: Callable[[], Coroutine[object, object, None]],
) -> Callable[[], None]:
    def wrapper() -> None:
        asyncio.run(test())

    return wrapper


def _usage(
    *,
    requests: int = 1,
    input_tokens: int = 10,
    output_tokens: int = 5,
    cached_input_tokens: int = 2,
    reasoning_tokens: int = 1,
) -> AgentTokenUsage:
    return AgentTokenUsage(
        requests=requests,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cached_input_tokens=cached_input_tokens,
        reasoning_tokens=reasoning_tokens,
    )


def _record(
    trace_id: str = TRACE_A,
    *,
    request_id: str = REQUEST_A,
    agent: AgentKind = AgentKind.ROUTER,
    usage: AgentTokenUsage | None = None,
    status: RuntimeResultStatus = RuntimeResultStatus.SUCCESS,
) -> AgentTraceRecord:
    stage_usage = usage or _usage()
    return AgentTraceRecord(
        trace_id=trace_id,
        request_id=request_id,
        runtime_status=status,
        stages=(
            AgentStageObservation(
                agent=agent,
                status=StageStatus.SUCCESS,
                duration_ms=12.5,
                attempt_count=1,
                usage=stage_usage,
            ),
        ),
        usage=stage_usage,
        warning_count=0,
        failure_count=0,
    )


def test_observability_contracts_are_strict_frozen_and_extra_forbidden() -> None:
    usage = _usage()
    with pytest.raises(ValidationError):
        AgentTokenUsage.model_validate(
            {**usage.model_dump(), "provider": "forbidden"}
        )
    with pytest.raises(ValidationError):
        AgentTokenUsage.model_validate(
            {
                "requests": 1.0,
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            }
        )
    with pytest.raises(ValidationError):
        AgentTokenUsage(
            requests=-1,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
        )
    with pytest.raises(ValidationError):
        AgentTokenUsage(
            requests=1,
            input_tokens=10,
            output_tokens=5,
            total_tokens=14,
        )
    with pytest.raises(ValidationError):
        usage.requests = 2


@pytest.mark.parametrize(
    "trace_id",
    (
        "trace_short",
        "trace_0000000000000000000000000000000G",
        "00000000000000000000000000000000000000",
        "TRACE_00000000000000000000000000000000",
    ),
)
def test_trace_id_format_rejects_malformed_values(trace_id: str) -> None:
    with pytest.raises(ValidationError):
        AgentTraceQuery(trace_id=trace_id)


def test_trace_record_rejects_duplicate_order_and_usage_mismatch() -> None:
    first = _record()
    router_stage = first.stages[0]
    discovery_stage = AgentStageObservation(
        agent=AgentKind.DISCOVERY,
        status=StageStatus.SUCCESS,
        duration_ms=1.0,
        attempt_count=1,
        usage=AgentTokenUsage(),
    )
    for stages in (
        (router_stage, router_stage),
        (discovery_stage, router_stage),
    ):
        with pytest.raises(ValidationError):
            AgentTraceRecord(
                trace_id=TRACE_A,
                request_id=REQUEST_A,
                runtime_status=RuntimeResultStatus.SUCCESS,
                stages=stages,
                usage=first.usage,
                warning_count=0,
                failure_count=0,
            )
    with pytest.raises(ValidationError):
        AgentTraceRecord(
            trace_id=TRACE_A,
            request_id=REQUEST_A,
            runtime_status=RuntimeResultStatus.SUCCESS,
            stages=first.stages,
            usage=AgentTokenUsage(),
            warning_count=0,
            failure_count=0,
        )


def test_zero_attempt_representation_is_only_failed_and_zero_usage() -> None:
    valid = AgentStageObservation(
        agent=AgentKind.ITINERARY,
        status=StageStatus.FAILED,
        duration_ms=0.0,
        attempt_count=0,
        usage=AgentTokenUsage(),
        failure_code=FailureCode.INVALID_INPUT,
    )
    assert valid.attempt_count == 0
    with pytest.raises(ValidationError):
        AgentStageObservation(
            agent=AgentKind.ITINERARY,
            status=StageStatus.SUCCESS,
            duration_ms=0.0,
            attempt_count=0,
            usage=AgentTokenUsage(),
        )


def test_public_schemas_have_no_content_or_location_escape_hatches() -> None:
    contract_types = (
        AgentTokenUsage,
        AgentStageObservation,
        AgentTraceRecord,
        AgentTraceQuery,
        AgentRequestTraceQuery,
        AgentUsageQuery,
    )
    schemas = tuple(contract.model_json_schema() for contract in contract_types)
    forbidden = {
        "query",
        "transcript",
        "origin",
        "latitude",
        "longitude",
        "output",
        "content",
        "metadata",
        "model",
        "provider",
        "price",
        "message",
        "uid",
        "email",
    }
    field_names = {
        field.casefold()
        for contract in contract_types
        for field in contract.model_fields
    }
    assert field_names.isdisjoint(forbidden)
    assert all(schema for schema in schemas)


@_run_async_test
async def test_store_query_summary_idempotency_conflict_and_fifo() -> None:
    store = InMemoryAgentObservabilityStore(capacity=2)
    first = _record()
    second = _record(
        TRACE_B,
        agent=AgentKind.DISCOVERY,
        usage=_usage(input_tokens=20, output_tokens=10),
    )
    third = _record(
        "trace_00000000000000000000000000000003",
        request_id="request-other",
    )
    await store.record(first)
    await store.record(first)
    await store.record(second)
    assert await store.get_trace(TRACE_A) == first
    listed = await store.list_for_request(REQUEST_A, limit=2)
    assert listed == (first, second)
    summary = await store.summarize(
        AgentUsageQuery(request_id=REQUEST_A)
    )
    assert summary.trace_count == 2
    assert summary.stage_count == 2
    assert summary.model_request_count == 2
    assert summary.total_tokens == 45
    assert tuple(item.agent for item in summary.per_agent) == (
        AgentKind.ROUTER,
        AgentKind.DISCOVERY,
    )
    assert (
        summary.model_dump_json()
        == (
            await store.summarize(
                AgentUsageQuery(request_id=REQUEST_A)
            )
        ).model_dump_json()
    )
    filtered = await store.summarize(
        AgentUsageQuery(
            request_id=REQUEST_A,
            agent=AgentKind.DISCOVERY,
        )
    )
    assert filtered.trace_count == 1
    assert filtered.total_tokens == 30

    await store.record(third)
    assert await store.get_trace(TRACE_A) is None
    assert await store.get_trace(TRACE_B) == second
    with pytest.raises(AgentObservabilityConflictError):
        await store.record(
            second.model_copy(
                update={"request_id": "request-conflict"}
            )
        )


@_run_async_test
async def test_store_empty_bounded_immutable_and_concurrent() -> None:
    store = InMemoryAgentObservabilityStore(capacity=20)
    empty = await store.summarize(
        AgentUsageQuery(request_id="request-empty")
    )
    assert empty.trace_count == empty.stage_count == 0
    assert empty.total_tokens == 0
    assert empty.per_agent == ()

    async def write(index: int) -> None:
        await store.record(
            _record(
                f"trace_{index:032x}",
                request_id="request-concurrent",
            )
        )

    async def read() -> None:
        await store.list_for_request("request-concurrent", limit=10)
        await store.summarize(
            AgentUsageQuery(
                request_id="request-concurrent",
                limit=10,
            )
        )

    await asyncio.gather(
        *(write(index) for index in range(1, 11)),
        *(read() for _ in range(10)),
    )
    records = await store.list_for_request(
        "request-concurrent",
        limit=5,
    )
    assert len(records) == 5
    with pytest.raises(ValidationError):
        records[0].request_id = "changed"


class _MaliciousQueryStore(AgentObservabilityStore):
    async def record(self, record: AgentTraceRecord) -> None:
        del record

    async def get_trace(self, trace_id: str) -> AgentTraceRecord | None:
        del trace_id
        raise RuntimeError("private-query-transcript")

    async def list_for_request(
        self,
        request_id: str,
        *,
        limit: int,
    ) -> tuple[AgentTraceRecord, ...]:
        del request_id, limit
        raise RuntimeError("private-coordinate-10.760001")

    async def summarize(
        self,
        query: AgentUsageQuery,
    ) -> Any:
        del query
        raise RuntimeError("private-stored-record")


def _assert_sanitized_exception(
    error: BaseException,
    *,
    expected_message: str,
    private_sentinel: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert str(error) == expected_message
    assert error.__cause__ is None
    assert error.__context__ is None
    formatted = "".join(
        traceback.format_exception(
            type(error),
            error,
            error.__traceback__,
        )
    )
    exposed = "\n".join((str(error), repr(error), formatted, caplog.text))
    assert private_sentinel not in exposed


@pytest.mark.parametrize(
    ("operation", "private_sentinel"),
    (
        ("get_trace", "private-query-transcript"),
        ("list_for_request", "private-coordinate-10.760001"),
        ("summarize", "private-stored-record"),
    ),
)
def test_public_queries_discard_malicious_store_exceptions(
    operation: str,
    private_sentinel: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = AgentObservabilityService(store=_MaliciousQueryStore())

    async def query() -> None:
        if operation == "get_trace":
            await service.get_trace(AgentTraceQuery(trace_id=TRACE_A))
        elif operation == "list_for_request":
            await service.list_for_request(
                AgentRequestTraceQuery(request_id=REQUEST_A)
            )
        else:
            await service.summarize(
                AgentUsageQuery(request_id=REQUEST_A)
            )

    with pytest.raises(AgentObservabilityQueryError) as raised:
        asyncio.run(query())
    _assert_sanitized_exception(
        raised.value,
        expected_message="Observability query failed.",
        private_sentinel=private_sentinel,
        caplog=caplog,
    )


def test_public_query_cancellation_propagates() -> None:
    class _CancellingStore(_MaliciousQueryStore):
        async def get_trace(
            self,
            trace_id: str,
        ) -> AgentTraceRecord | None:
            del trace_id
            raise asyncio.CancelledError

        async def list_for_request(
            self,
            request_id: str,
            *,
            limit: int,
        ) -> tuple[AgentTraceRecord, ...]:
            del request_id, limit
            raise asyncio.CancelledError

        async def summarize(
            self,
            query: AgentUsageQuery,
        ) -> Any:
            del query
            raise asyncio.CancelledError

    service = AgentObservabilityService(store=_CancellingStore())

    async def scenario() -> None:
        calls = (
            service.get_trace(AgentTraceQuery(trace_id=TRACE_A)),
            service.list_for_request(
                AgentRequestTraceQuery(request_id=REQUEST_A)
            ),
            service.summarize(AgentUsageQuery(request_id=REQUEST_A)),
        )
        for call in calls:
            with pytest.raises(asyncio.CancelledError):
                await call

    asyncio.run(scenario())


def test_store_conversions_discard_validation_and_overflow_details(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import app.agents.observability.store as store_module
    from app.agents.observability.contracts import MAX_TOKEN_COUNT

    private_record = "private-invalid-record"
    invalid_record = SimpleNamespace(
        model_dump=lambda **kwargs: {
            "request_id": private_record,
            "unexpected": kwargs,
        }
    )
    with pytest.raises(AgentObservabilityStoreError) as copy_error:
        store_module._copy_record(cast(AgentTraceRecord, invalid_record))
    _assert_sanitized_exception(
        copy_error.value,
        expected_message="Trace record validation failed.",
        private_sentinel=private_record,
        caplog=caplog,
    )

    maximum = _usage(
        requests=0,
        input_tokens=MAX_TOKEN_COUNT,
        output_tokens=0,
        cached_input_tokens=0,
        reasoning_tokens=0,
    )
    with pytest.raises(AgentObservabilityStoreError) as aggregate_error:
        store_module._summarize(
            (
                _record(TRACE_A, usage=maximum),
                _record(TRACE_B, usage=maximum),
            ),
            AgentUsageQuery(request_id=REQUEST_A),
        )
    _assert_sanitized_exception(
        aggregate_error.value,
        expected_message="Usage aggregate exceeds safe bounds.",
        private_sentinel=str(MAX_TOKEN_COUNT * 2),
        caplog=caplog,
    )

    private_summary = "private-summary-value"

    def fail_summary(**kwargs: object) -> None:
        del kwargs
        raise ValueError(private_summary)

    monkeypatch.setattr(store_module, "AgentUsageSummary", fail_summary)
    with pytest.raises(AgentObservabilityStoreError) as summary_error:
        store_module._summarize(
            (_record(),),
            AgentUsageQuery(request_id=REQUEST_A),
        )
    _assert_sanitized_exception(
        summary_error.value,
        expected_message="Usage summary validation failed.",
        private_sentinel=private_summary,
        caplog=caplog,
    )


@_run_async_test
async def test_context_propagates_isolates_and_restores_nested_attempts() -> None:
    async def child() -> tuple[str, AgentKind | None, int | None]:
        identity = current_observation_identity()
        assert identity is not None
        return identity.request_id, identity.agent, identity.attempt

    async def request_scope(
        request_id: str,
        trace_id: str,
    ) -> tuple[str, AgentKind | None, int | None]:
        with bind_request_observation(
            request_id=request_id,
            trace_id=trace_id,
            sdk_export_enabled=False,
        ):
            with observation_attempt(AgentKind.ROUTER, 1):
                outer = current_observation_identity()
                assert outer is not None
                with observation_attempt(AgentKind.DISCOVERY, 2):
                    nested = await asyncio.create_task(child())
                restored = current_observation_identity()
                assert restored == outer
                return nested

    first, second = await asyncio.gather(
        request_scope("request-one", TRACE_A),
        request_scope("request-two", TRACE_B),
    )
    assert first == ("request-one", AgentKind.DISCOVERY, 2)
    assert second == ("request-two", AgentKind.DISCOVERY, 2)
    assert current_observation_identity() is None


@_run_async_test
async def test_context_resets_after_exception_and_cancellation() -> None:
    with pytest.raises(RuntimeError):
        with bind_request_observation(
            request_id=REQUEST_A,
            trace_id=TRACE_A,
            sdk_export_enabled=False,
        ):
            raise RuntimeError("controlled")
    assert current_observation_identity() is None

    started = asyncio.Event()

    async def cancelled() -> None:
        with bind_request_observation(
            request_id=REQUEST_A,
            trace_id=TRACE_A,
            sdk_export_enabled=False,
        ):
            started.set()
            await asyncio.Future()

    task = asyncio.create_task(cancelled())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert current_observation_identity() is None


def test_sdk_usage_adapter_maps_details_and_ignores_request_entries() -> None:
    usage = Usage(
        requests=2,
        input_tokens=100,
        input_tokens_details=InputTokensDetails(
            cached_tokens=40,
            cache_write_tokens=7,
        ),
        output_tokens=30,
        output_tokens_details=OutputTokensDetails(
            reasoning_tokens=9,
        ),
        total_tokens=130,
    )
    cast(Any, usage).request_usage_entries = ["forbidden-entry"]
    assert token_usage_from_sdk(usage) == AgentTokenUsage(
        requests=2,
        input_tokens=100,
        output_tokens=30,
        total_tokens=130,
        cached_input_tokens=40,
        reasoning_tokens=9,
    )
    usage.input_tokens_details = cast(InputTokensDetails, None)
    usage.output_tokens_details = cast(OutputTokensDetails, None)
    assert token_usage_from_sdk(usage).cached_input_tokens == 0
    assert token_usage_from_sdk(usage).reasoning_tokens == 0


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("requests", -1),
        ("input_tokens", 1.5),
        ("output_tokens", True),
        ("total_tokens", -1),
    ),
)
def test_sdk_usage_adapter_fails_closed(
    field: str,
    value: object,
) -> None:
    usage = Usage(
        requests=1,
        input_tokens=2,
        output_tokens=3,
        total_tokens=5,
    )
    setattr(usage, field, value)
    with pytest.raises(AgentUsageAdaptationError):
        token_usage_from_sdk(usage)


def test_completed_sdk_usage_attaches_once_to_current_agent() -> None:
    sdk_usage = Usage(
        requests=1,
        input_tokens=8,
        output_tokens=2,
        total_tokens=10,
    )
    result = SimpleNamespace(
        context_wrapper=SimpleNamespace(usage=sdk_usage)
    )
    second_result = SimpleNamespace(
        context_wrapper=SimpleNamespace(
            usage=Usage(
                requests=1,
                input_tokens=4,
                output_tokens=1,
                total_tokens=5,
            )
        )
    )
    with bind_request_observation(
        request_id=REQUEST_A,
        trace_id=TRACE_A,
        sdk_export_enabled=False,
    ) as accumulator:
        with observation_attempt(AgentKind.ROUTER, 1):
            assert capture_sdk_result_usage(result) is True
            assert capture_sdk_result_usage(second_result) is True
        assert accumulator.attempt_count(AgentKind.ROUTER) == 1
        assert accumulator.usage_for(AgentKind.ROUTER) == AgentTokenUsage(
            requests=2,
            input_tokens=12,
            output_tokens=3,
            total_tokens=15,
            cached_input_tokens=0,
            reasoning_tokens=0,
        )
        assert capture_usage_for_current_attempt(_usage()) is False

    class _BrokenResult:
        @property
        def context_wrapper(self) -> object:
            raise RuntimeError("private provider detail")

    assert capture_sdk_result_usage(_BrokenResult()) is False


def test_run_config_is_fresh_private_and_sensitive_tracing_is_always_off() -> None:
    base = RunConfig(
        tracing_disabled=True,
        trace_include_sensitive_data=False,
    )
    provider = base.model_provider
    outside = run_config_for_observation(base)
    assert outside is not base
    assert outside.model_provider is provider
    assert outside.tracing_disabled is True
    assert outside.trace_include_sensitive_data is False

    with bind_request_observation(
        request_id=REQUEST_A,
        trace_id=TRACE_A,
        sdk_export_enabled=False,
    ):
        local = run_config_for_observation(base)
    assert local.tracing_disabled is True
    assert local.trace_include_sensitive_data is False

    with bind_request_observation(
        request_id=REQUEST_A,
        trace_id=TRACE_A,
        sdk_export_enabled=True,
    ):
        exported = run_config_for_observation(base)
    assert exported.tracing_disabled is False
    assert exported.trace_include_sensitive_data is False
    assert exported.model_provider is provider
    assert exported.workflow_name == WORKFLOW_NAME
    assert exported.trace_id == TRACE_A
    assert exported.group_id == REQUEST_A
    assert exported.trace_metadata == {"request_id": REQUEST_A}
    assert base.tracing_disabled is True
    assert base.trace_id is None


@_run_async_test
async def test_concurrent_run_configs_do_not_mutate_each_other() -> None:
    base = RunConfig(
        tracing_disabled=True,
        trace_include_sensitive_data=False,
    )

    async def build(
        request_id: str,
        trace_id: str,
        exported: bool,
    ) -> RunConfig:
        with bind_request_observation(
            request_id=request_id,
            trace_id=trace_id,
            sdk_export_enabled=exported,
        ):
            await asyncio.sleep(0)
            return run_config_for_observation(base)

    enabled, disabled = await asyncio.gather(
        build("request-exported", TRACE_A, True),
        build("request-local", TRACE_B, False),
    )
    assert enabled.tracing_disabled is False
    assert enabled.group_id == "request-exported"
    assert disabled.tracing_disabled is True
    assert disabled.group_id is None
    assert base.tracing_disabled is True


def test_sdk_workflow_and_attempt_metadata_are_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.agents.observability.sdk as sdk_module

    captured_trace: dict[str, object] = {}
    captured_span: dict[str, object] = {}

    class _Trace:
        def start(self, *, mark_as_current: bool) -> None:
            captured_trace["mark_as_current"] = mark_as_current

    class _Span:
        def start(self, *, mark_as_current: bool) -> None:
            captured_span["mark_as_current"] = mark_as_current

        def finish(self, *, reset_current: bool) -> None:
            captured_span["reset_current"] = reset_current

    def fake_trace(**kwargs: object) -> _Trace:
        captured_trace.update(kwargs)
        return _Trace()

    def fake_span(name: str, data: object) -> _Span:
        captured_span["name"] = name
        captured_span["data"] = data
        return _Span()

    monkeypatch.setattr(sdk_module, "trace", fake_trace)
    monkeypatch.setattr(sdk_module, "custom_span", fake_span)
    start_workflow_trace(
        trace_id=TRACE_A,
        request_id=REQUEST_A,
        tracing_api_key="secret-not-exported-in-metadata",
    )
    assert captured_trace["workflow_name"] == WORKFLOW_NAME
    assert captured_trace["trace_id"] == TRACE_A
    assert captured_trace["group_id"] == REQUEST_A
    assert captured_trace["metadata"] == {"request_id": REQUEST_A}
    assert set(cast(dict[str, object], captured_trace["metadata"])) == {
        "request_id"
    }

    with bind_request_observation(
        request_id=REQUEST_A,
        trace_id=TRACE_A,
        sdk_export_enabled=True,
    ):
        with sdk_attempt_span(AgentKind.NARRATION, 2):
            pass
    assert captured_span["name"] == ATTEMPT_SPAN_NAME
    assert captured_span["data"] == {
        "agent": AgentKind.NARRATION.value,
        "attempt": 2,
    }


def test_export_policy_is_explicit_secret_safe_and_store_is_injected() -> None:
    store = InMemoryAgentObservabilityStore(capacity=1)
    policy = AgentObservabilityPolicy(
        sdk_trace_export_enabled=True,
        tracing_api_key=SecretStr("trace-secret"),
    )
    service = AgentObservabilityService(store=store, policy=policy)
    assert service is not None
    assert "trace-secret" not in repr(policy)
    assert AgentObservabilityPolicy().sdk_trace_export_enabled is False
    with pytest.raises(ValidationError):
        AgentObservabilityPolicy(sdk_trace_export_enabled=True)
    with pytest.raises(TypeError):
        AgentObservabilityService()  # type: ignore[call-arg]


@pytest.mark.parametrize(("module_name", "agent"), SDK_ADAPTER_CASES)
def test_all_seven_real_sdk_adapters_observe_context_behaviorally(
    module_name: str,
    agent: AgentKind,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = importlib.import_module(
        f"app.agents.{module_name}.executor"
    )
    runner = cast(Any, getattr(module, "_AgentsSdkRunner"))()
    captured_configs: list[RunConfig] = []
    expected_usage = AgentTokenUsage(
        requests=1,
        input_tokens=11,
        output_tokens=4,
        total_tokens=15,
        cached_input_tokens=0,
        reasoning_tokens=0,
    )

    async def fake_run(
        starting_agent: object,
        model_input: str,
        **kwargs: object,
    ) -> object:
        del starting_agent, model_input
        run_config = cast(RunConfig, kwargs["run_config"])
        captured_configs.append(run_config)
        await asyncio.sleep(0)
        return SimpleNamespace(
            final_output=object(),
            context_wrapper=SimpleNamespace(
                usage=Usage(
                    requests=1,
                    input_tokens=11,
                    output_tokens=4,
                    total_tokens=15,
                )
            ),
        )

    monkeypatch.setattr(
        cast(Any, getattr(module, "Runner")),
        "run",
        fake_run,
    )
    base = RunConfig(
        tracing_disabled=True,
        trace_include_sensitive_data=False,
    )
    provider = base.model_provider

    async def invoke(config: RunConfig) -> None:
        kwargs: dict[str, object] = {
            "max_turns": 1,
            "run_config": config,
        }
        if module_name == "discovery":
            kwargs["context"] = object()
        await runner.run(object(), "safe-input", **kwargs)

    async def observed(
        *,
        request_id: str,
        trace_id: str,
        exported: bool,
    ) -> tuple[RunConfig, AgentTokenUsage, int]:
        with bind_request_observation(
            request_id=request_id,
            trace_id=trace_id,
            sdk_export_enabled=exported,
        ) as accumulator:
            with observation_attempt(agent, 1):
                await asyncio.sleep(0)
                config = run_config_for_observation(base)
                await invoke(config)
            return (
                config,
                accumulator.usage_for(agent),
                accumulator.attempt_count(agent),
            )

    async def scenario() -> None:
        outside = run_config_for_observation(base)
        await invoke(outside)
        assert outside is not base
        assert outside.tracing_disabled is True
        assert outside.trace_include_sensitive_data is False

        local, local_usage, local_attempts = await observed(
            request_id="request-local",
            trace_id=TRACE_A,
            exported=False,
        )
        assert local.tracing_disabled is True
        assert local.trace_include_sensitive_data is False
        assert local_usage == expected_usage
        assert local_attempts == 1

        exported, exported_usage, exported_attempts = await observed(
            request_id=REQUEST_A,
            trace_id=TRACE_A,
            exported=True,
        )
        assert exported.tracing_disabled is False
        assert exported.trace_include_sensitive_data is False
        assert exported.trace_id == TRACE_A
        assert exported.group_id == REQUEST_A
        assert exported_usage == expected_usage
        assert exported_attempts == 1

        enabled_result, disabled_result = await asyncio.gather(
            observed(
                request_id="request-concurrent-exported",
                trace_id=TRACE_A,
                exported=True,
            ),
            observed(
                request_id="request-concurrent-local",
                trace_id=TRACE_B,
                exported=False,
            ),
        )
        enabled, enabled_usage, enabled_attempts = enabled_result
        disabled, disabled_usage, disabled_attempts = disabled_result
        assert enabled.tracing_disabled is False
        assert enabled.trace_id == TRACE_A
        assert enabled.group_id == "request-concurrent-exported"
        assert disabled.tracing_disabled is True
        assert disabled.trace_id is None
        assert disabled.group_id is None
        assert enabled.trace_include_sensitive_data is False
        assert disabled.trace_include_sensitive_data is False
        assert enabled_usage == disabled_usage == expected_usage
        assert enabled_attempts == disabled_attempts == 1

    asyncio.run(scenario())
    assert len(captured_configs) == 5
    assert len({id(config) for config in captured_configs}) == 5
    assert all(config is not base for config in captured_configs)
    assert all(config.model_provider is provider for config in captured_configs)
    assert base.tracing_disabled is True
    assert base.trace_include_sensitive_data is False
    assert base.trace_id is None
    assert base.group_id is None


def test_all_seven_sdk_adapters_use_central_helpers_in_source() -> None:
    modules = (
        "router",
        "discovery",
        "narration",
        "local_culture",
        "itinerary",
        "grounding",
        "composer",
    )
    for module in modules:
        source = (
            BACKEND
            / "app"
            / "agents"
            / module
            / "executor.py"
        ).read_text(encoding="utf-8")
        assert "run_config_for_observation(self._run_config)" in source
        assert "capture_sdk_result_usage(result)" in source
        assert "trace_include_sensitive_data=False" in source
        assert "enable_verbose_stdout_logging" not in source


def test_observability_has_no_module_level_store_or_external_dependency() -> None:
    import app.agents.observability.service as service_module
    import app.agents.observability.store as store_module

    source = inspect.getsource(service_module) + inspect.getsource(store_module)
    forbidden = (
        "sqlalchemy",
        "FastAPI",
        "APIRouter",
        "opentelemetry",
        "prometheus",
        "sentry",
        "datadog",
    )
    assert not any(value.casefold() in source.casefold() for value in forbidden)
    assert not any(
        isinstance(value, InMemoryAgentObservabilityStore)
        for value in vars(service_module).values()
    )
