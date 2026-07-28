"""Typed read-only menu boundary and injected SQLAlchemy adapter."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Protocol, cast, runtime_checkable

from pydantic import Field, HttpUrl, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.contracts import SourceType
from app.agents.discovery.models import (
    MAX_MENU_ITEMS,
    MenuItemResult,
    MenuResultEnvelope,
    PrivateToolModel,
    ToolSource,
)
from app.db.models import MenuItem, Poi, Source
from app.providers.poi.models import MAX_DISCOVERY_RESULTS


class MenuErrorCode(StrEnum):
    """Stable private failure categories for menu reads."""

    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_OUTPUT = "invalid_output"


class MenuReaderError(Exception):
    """Sanitized menu boundary failure without database exception details."""

    __slots__ = ("code",)

    def __init__(self, code: MenuErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class MenuTimeoutPolicy(PrivateToolModel):
    """Bounded deadline for one menu read."""

    seconds: Annotated[
        float,
        Field(strict=True, gt=0, le=60, allow_inf_nan=False),
    ] = 5.0


@runtime_checkable
class PoiMenuReader(Protocol):
    """Read normalized menus only for caller-selected curated POIs."""

    async def read_menu_items(
        self,
        poi_provider_ids: tuple[str, ...],
    ) -> MenuResultEnvelope:
        """Return empty success when selected POIs have no menu rows."""
        ...


class SqlAlchemyPoiMenuReader:
    """Map one injected-session, read-only query into strict menu values."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        timeout_policy: MenuTimeoutPolicy | None = None,
    ) -> None:
        self._session = session
        self._timeout_policy = timeout_policy or MenuTimeoutPolicy()

    async def read_menu_items(
        self,
        poi_provider_ids: tuple[str, ...],
    ) -> MenuResultEnvelope:
        """Read one selected set while preserving caller cancellation."""
        selected_ids = _validated_selected_ids(poi_provider_ids)
        if not selected_ids:
            return MenuResultEnvelope()
        try:
            async with asyncio.timeout(self._timeout_policy.seconds):
                return await self._read(selected_ids)
        except TimeoutError:
            raise MenuReaderError(MenuErrorCode.TIMEOUT) from None
        except asyncio.CancelledError:
            raise
        except MenuReaderError:
            raise
        except SQLAlchemyError:
            raise MenuReaderError(MenuErrorCode.UNAVAILABLE) from None
        except Exception:
            raise MenuReaderError(MenuErrorCode.INVALID_OUTPUT) from None

    async def _read(
        self,
        selected_ids: tuple[str, ...],
    ) -> MenuResultEnvelope:
        statement = (
            select(
                MenuItem.id.label("menu_item_id"),
                MenuItem.poi_id.label("poi_provider_id"),
                MenuItem.item_name,
                MenuItem.price_minor_units,
                MenuItem.currency_code,
                MenuItem.source_type.label("menu_source_type"),
                MenuItem.source_updated_at,
                Source.id.label("source_id"),
                Source.source_type.label("source_type"),
                Source.label.label("source_label"),
                Source.publisher,
                Source.url.label("source_url"),
                Source.published_at,
                Source.retrieved_at,
            )
            .select_from(MenuItem)
            .join(Poi, Poi.id == MenuItem.poi_id)
            .join(Source, Source.id == MenuItem.source_id)
            .where(
                MenuItem.poi_id.in_(selected_ids),
                Poi.id.in_(selected_ids),
            )
            .order_by(MenuItem.poi_id, MenuItem.id)
            .limit(MAX_MENU_ITEMS + 1)
        )
        rows = cast(
            Sequence[Mapping[str, object]],
            (await self._session.execute(statement)).mappings().all(),
        )
        if len(rows) > MAX_MENU_ITEMS:
            raise MenuReaderError(MenuErrorCode.INVALID_OUTPUT)
        try:
            items = tuple(_normalize_row(row) for row in rows)
            result = MenuResultEnvelope(items=items)
        except (TypeError, ValueError, ValidationError):
            raise MenuReaderError(MenuErrorCode.INVALID_OUTPUT) from None
        if any(item.poi_provider_id not in selected_ids for item in result.items):
            raise MenuReaderError(MenuErrorCode.INVALID_OUTPUT)
        return result


def _validated_selected_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) > MAX_DISCOVERY_RESULTS:
        raise MenuReaderError(MenuErrorCode.INVALID_OUTPUT)
    if len(values) != len(set(values)):
        raise MenuReaderError(MenuErrorCode.INVALID_OUTPUT)
    for value in values:
        if (
            not isinstance(value, str)
            or not value.strip()
            or value != value.strip()
            or len(value) > 255
        ):
            raise MenuReaderError(MenuErrorCode.INVALID_OUTPUT)
    return values


def _normalize_row(row: Mapping[str, object]) -> MenuItemResult:
    source_type = SourceType(_required_str(row["source_type"]))
    menu_source_type = SourceType(_required_str(row["menu_source_type"]))
    if source_type is not menu_source_type:
        raise ValueError("Menu source type does not match source.")
    source_url = _optional_str(row["source_url"])
    source = ToolSource(
        source_id=_required_str(row["source_id"]),
        source_type=source_type,
        label=_required_str(row["source_label"]),
        publisher=_optional_str(row["publisher"]),
        url=HttpUrl(source_url) if source_url is not None else None,
        published_at=_datetime_or_none(row["published_at"]),
        retrieved_at=_datetime_or_none(row["retrieved_at"]),
    )
    return MenuItemResult(
        menu_item_id=_required_str(row["menu_item_id"]),
        poi_provider_id=_required_str(row["poi_provider_id"]),
        item_name=_required_str(row["item_name"]),
        price_minor_units=_required_int(row["price_minor_units"]),
        currency=_required_str(row["currency_code"]),
        source_updated_at=_required_datetime(row["source_updated_at"]),
        source=source,
    )


def _required_str(value: object) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("Expected string.")


def _optional_str(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise TypeError("Expected optional string.")


def _required_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("Expected integer.")
    return value


def _required_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError("Expected datetime.")


def _datetime_or_none(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    raise TypeError("Expected optional datetime.")
