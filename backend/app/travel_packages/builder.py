"""Offline deterministic build, atomic write, drift check, and verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.data_pipeline.loader import LoadedPackage, load_package
from app.data_pipeline.models import CuratedPackageV1, SourceRecord
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.travel_packages.models import (
    ARTIFACT_SCHEMA_VERSION,
    JSON_MEDIA_TYPE,
    MANIFEST_SCHEMA_VERSION,
    ArtifactMenuItemV1,
    ArtifactNarrationV1,
    ArtifactPackageMetadataV1,
    ArtifactPoiManifestV1,
    ArtifactPoiV1,
    TravelPackageArtifactV1,
    TravelPackageManifestV1,
)
from app.travel_packages.paths import (
    COMMITTED_ARTIFACT_ROOT,
    COMMITTED_CITY,
)

CITY_DISPLAY_NAMES = {
    "hcmc": "Ho Chi Minh City",
    "bkk": "Bangkok",
}
UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class ArtifactBuildError(RuntimeError):
    """Safe build failure suitable for CLI output."""


class ArtifactVerificationError(RuntimeError):
    """Safe verification failure suitable for CLI output."""


@dataclass(frozen=True)
class BuildResult:
    """Paths and verified metadata for one completed build."""

    data_path: Path
    manifest_path: Path
    manifest: TravelPackageManifestV1
    artifact: TravelPackageArtifactV1


@dataclass(frozen=True)
class VerificationResult:
    """Validated manifest/data pair."""

    manifest_path: Path
    data_path: Path
    manifest: TravelPackageManifestV1
    artifact: TravelPackageArtifactV1


def canonical_json_bytes(model: TravelPackageArtifactV1 | TravelPackageManifestV1) -> bytes:
    """Serialize canonical UTF-8 JSON with sorted keys and one final newline."""
    document = model.model_dump(mode="json", by_alias=True)
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _epoch_millis(value: datetime) -> int:
    normalized = value.astimezone(timezone.utc)
    delta = normalized - UTC_EPOCH
    return (
        delta.days * 86_400_000
        + delta.seconds * 1_000
        + delta.microseconds // 1_000
    )


def _rfc3339_utc(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    rendered = normalized.isoformat(timespec="microseconds")
    rendered = rendered.removesuffix("+00:00")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return f"{rendered}Z"


def _source_freshness(
    source: SourceRecord,
    package_published_at: datetime,
) -> datetime:
    return (
        source.retrieved_at
        or source.published_at
        or package_published_at
    )


def _latest_poi_freshness(
    source_ids: tuple[str, ...],
    sources: dict[str, SourceRecord],
    package_published_at: datetime,
) -> datetime:
    return max(
        _source_freshness(sources[source_id], package_published_at)
        for source_id in source_ids
    )


def artifact_from_curated(
    package: CuratedPackageV1,
) -> TravelPackageArtifactV1:
    """Map a validated authoring model through the explicit public allowlist."""
    metadata = package.package
    city = CITY_DISPLAY_NAMES[metadata.city_code.value]
    sources = {source.id: source for source in package.sources}
    pois = tuple(
        ArtifactPoiV1(
            poiId=poi.id,
            name=poi.canonical_name,
            city=city,
            area=poi.area,
            category=poi.category,
            latitude=poi.location.latitude,
            longitude=poi.location.longitude,
            address=poi.address,
            shortDescription=poi.short_description,
            status="curated",
            updatedAtEpochMillis=_epoch_millis(
                _latest_poi_freshness(
                    poi.source_ids,
                    sources,
                    metadata.published_at,
                )
            ),
        )
        for poi in sorted(package.pois, key=lambda record: record.id)
    )
    menu_items = tuple(
        ArtifactMenuItemV1(
            menuItemId=item.id,
            poiId=item.poi_id,
            dishName=item.item_name,
            priceMinorUnits=item.price_minor_units,
            currencyCode=item.currency_code,
            sourceType=item.source_type,
            updatedAtEpochMillis=_epoch_millis(
                item.source_updated_at
            ),
        )
        for item in sorted(package.menu_items, key=lambda record: record.id)
    )
    narrations: list[ArtifactNarrationV1] = []
    for narration in sorted(
        package.narrations,
        key=lambda record: record.id,
    ):
        source = (
            sources[narration.source_id]
            if narration.source_id is not None
            else None
        )
        source_label = (
            source.label
            if source is not None
            else narration.fallback_source_label
        )
        if source_label is None:
            raise ArtifactBuildError(
                "validated narration has no public source label"
            )
        freshness = (
            _source_freshness(source, metadata.published_at)
            if source is not None
            else metadata.published_at
        )
        narrations.append(
            ArtifactNarrationV1(
                narrationId=narration.id,
                poiId=narration.poi_id,
                languageCode=narration.language_code,
                content=narration.content,
                verificationStatus=narration.verification_status,
                generatedAtEpochMillis=_epoch_millis(freshness),
                sourceLabel=source_label,
            )
        )

    poi_ids = tuple(record.poi_id for record in pois)
    return TravelPackageArtifactV1(
        formatVersion=ARTIFACT_SCHEMA_VERSION,
        packageMetadata=ArtifactPackageMetadataV1(
            packageId=metadata.package_id,
            city=city,
            version=metadata.content_version,
            publishedAtEpochMillis=_epoch_millis(
                metadata.published_at
            ),
            manifest=ArtifactPoiManifestV1(
                formatVersion=ARTIFACT_SCHEMA_VERSION,
                poiIds=poi_ids,
            ),
        ),
        pois=pois,
        aliases=(),
        menuItems=menu_items,
        narrations=tuple(narrations),
    )


def artifact_filenames(
    package_id: str,
    content_version: str,
) -> tuple[str, str]:
    """Return bounded deterministic names from already validated identity."""
    stem = f"{package_id}-{content_version}"
    if len(stem) > 160 or any(
        token in stem for token in ("/", "\\", "..")
    ):
        raise ArtifactBuildError("unsafe package identity for file naming")
    return (f"{stem}.data.json", f"{stem}.manifest.json")


def _stage_file(directory: Path, filename: str, content: bytes) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        dir=directory,
        prefix=f".{filename}.",
        suffix=".tmp",
    )
    path = Path(raw_path)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def _restore_file(path: Path, previous: bytes | None) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
        return
    staged = _stage_file(path.parent, path.name, previous)
    try:
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def _write_pair_atomically(
    output_dir: Path,
    data_filename: str,
    data_bytes: bytes,
    manifest_filename: str,
    manifest_bytes: bytes,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not output_dir.is_dir():
        raise ArtifactBuildError("output directory is not a directory")
    data_path = output_dir / data_filename
    manifest_path = output_dir / manifest_filename
    if (
        data_path.parent.resolve() != output_dir.resolve()
        or manifest_path.parent.resolve() != output_dir.resolve()
    ):
        raise ArtifactBuildError("artifact path escapes output directory")

    previous_data = data_path.read_bytes() if data_path.exists() else None
    previous_manifest = (
        manifest_path.read_bytes() if manifest_path.exists() else None
    )
    staged_data: Path | None = None
    staged_manifest: Path | None = None
    replaced_data = False
    try:
        staged_data = _stage_file(
            output_dir,
            data_filename,
            data_bytes,
        )
        staged_manifest = _stage_file(
            output_dir,
            manifest_filename,
            manifest_bytes,
        )
        os.replace(staged_data, data_path)
        replaced_data = True
        staged_data = None
        os.replace(staged_manifest, manifest_path)
        staged_manifest = None
    except BaseException as error:
        if replaced_data:
            try:
                _restore_file(data_path, previous_data)
                _restore_file(manifest_path, previous_manifest)
            except OSError:
                pass
        raise ArtifactBuildError("atomic artifact write failed") from error
    finally:
        if staged_data is not None:
            staged_data.unlink(missing_ok=True)
        if staged_manifest is not None:
            staged_manifest.unlink(missing_ok=True)
    return (data_path, manifest_path)


def build_loaded_package(
    loaded: LoadedPackage,
    output_dir: Path,
) -> BuildResult:
    """Build exactly one already validated curated package."""
    package = loaded.package
    artifact = artifact_from_curated(package)
    data_bytes = canonical_json_bytes(artifact)
    data_filename, manifest_filename = artifact_filenames(
        package.package.package_id,
        package.package.content_version,
    )
    manifest = TravelPackageManifestV1(
        schemaVersion=MANIFEST_SCHEMA_VERSION,
        artifactSchemaVersion=ARTIFACT_SCHEMA_VERSION,
        packageId=package.package.package_id,
        city=package.package.city_code,
        contentVersion=package.package.content_version,
        publishedAt=_rfc3339_utc(package.package.published_at),
        dataFilename=data_filename,
        mediaType=JSON_MEDIA_TYPE,
        byteSize=len(data_bytes),
        sha256=hashlib.sha256(data_bytes).hexdigest(),
    )
    manifest_bytes = canonical_json_bytes(manifest)
    data_path, manifest_path = _write_pair_atomically(
        output_dir,
        data_filename,
        data_bytes,
        manifest_filename,
        manifest_bytes,
    )
    return BuildResult(
        data_path=data_path,
        manifest_path=manifest_path,
        manifest=manifest,
        artifact=artifact,
    )


def build_package_path(
    source_path: Path,
    output_dir: Path,
) -> BuildResult:
    """Validate one source package completely before writing any artifact."""
    validation = load_package(source_path)
    if not validation.is_valid:
        rendered = "; ".join(
            issue.render() for issue in validation.issues
        )
        raise ArtifactBuildError(f"curated input validation failed: {rendered}")
    return build_loaded_package(validation.packages[0], output_dir)


def build_city_package(city: str, output_dir: Path) -> BuildResult:
    """Build exactly one selected supported city."""
    source_path = CITY_PACKAGE_PATHS.get(city)
    if source_path is None:
        raise ArtifactBuildError(f"unsupported city: {city}")
    return build_package_path(source_path, output_dir)


def _load_json_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactVerificationError(
            f"{label} is not valid UTF-8 JSON"
        ) from error
    if not isinstance(value, dict):
        raise ArtifactVerificationError(f"{label} must be a JSON object")
    return value


def _safe_relative_filename(value: str) -> bool:
    path = Path(value)
    return (
        not path.is_absolute()
        and path.name == value
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
    )


def verify_manifest(manifest_path: Path) -> VerificationResult:
    """Verify exact bytes, size, contract versions, and package identity."""
    try:
        manifest_raw = manifest_path.read_bytes()
    except OSError as error:
        raise ArtifactVerificationError(
            "manifest file could not be read"
        ) from error
    try:
        manifest = TravelPackageManifestV1.model_validate(
            _load_json_object(manifest_raw, "manifest")
        )
    except ValidationError as error:
        raise ArtifactVerificationError("manifest contract is invalid") from error
    if not _safe_relative_filename(manifest.data_filename):
        raise ArtifactVerificationError("manifest data filename is unsafe")

    data_path = manifest_path.parent / manifest.data_filename
    try:
        data_raw = data_path.read_bytes()
    except OSError as error:
        raise ArtifactVerificationError(
            "manifest data file could not be read"
        ) from error
    if len(data_raw) != manifest.byte_size:
        raise ArtifactVerificationError("data byte size does not match manifest")
    actual_checksum = hashlib.sha256(data_raw).hexdigest()
    if not hmac.compare_digest(actual_checksum, manifest.sha256):
        raise ArtifactVerificationError("data SHA-256 does not match manifest")
    try:
        artifact = TravelPackageArtifactV1.model_validate(
            _load_json_object(data_raw, "data file")
        )
    except ValidationError as error:
        raise ArtifactVerificationError(
            "data file contract is invalid"
        ) from error

    metadata = artifact.package_metadata
    expected_data_filename, _ = artifact_filenames(
        metadata.package_id,
        metadata.version,
    )
    expected_city = CITY_DISPLAY_NAMES[manifest.city.value]
    if metadata.package_id != manifest.package_id:
        raise ArtifactVerificationError("package identity does not match manifest")
    if metadata.city != expected_city:
        raise ArtifactVerificationError("package city does not match manifest")
    if metadata.version != manifest.content_version:
        raise ArtifactVerificationError("package version does not match manifest")
    if metadata.published_at_epoch_millis != _epoch_millis(
        datetime.fromisoformat(
            manifest.published_at.replace("Z", "+00:00")
        )
    ):
        raise ArtifactVerificationError(
            "package publication timestamp does not match manifest"
        )
    if manifest.data_filename != expected_data_filename:
        raise ArtifactVerificationError(
            "data filename does not match package identity"
        )
    return VerificationResult(
        manifest_path=manifest_path,
        data_path=data_path,
        manifest=manifest,
        artifact=artifact,
    )


def committed_output_dir(city: str = COMMITTED_CITY) -> Path:
    """Resolve the versioned repository-owned output directory."""
    validation = load_package(CITY_PACKAGE_PATHS[city])
    if not validation.is_valid:
        raise ArtifactBuildError("committed curated input is invalid")
    version = validation.packages[0].package.package.content_version
    return COMMITTED_ARTIFACT_ROOT / city / version


def check_committed_artifact(
    city: str = COMMITTED_CITY,
) -> VerificationResult:
    """Fail if committed city bytes drift from current input or builder logic."""
    if city not in CITY_PACKAGE_PATHS:
        raise ArtifactBuildError(f"unsupported city: {city}")
    output_dir = committed_output_dir(city)
    package_validation = load_package(CITY_PACKAGE_PATHS[city])
    if not package_validation.is_valid:
        raise ArtifactBuildError("committed curated input is invalid")
    package = package_validation.packages[0].package.package
    data_filename, manifest_filename = artifact_filenames(
        package.package_id,
        package.content_version,
    )
    committed_data = output_dir / data_filename
    committed_manifest = output_dir / manifest_filename
    if not committed_data.is_file() or not committed_manifest.is_file():
        raise ArtifactBuildError("committed artifact files are missing")

    with tempfile.TemporaryDirectory(prefix="travel-package-check-") as raw:
        generated = build_city_package(city, Path(raw))
        if generated.data_path.read_bytes() != committed_data.read_bytes():
            raise ArtifactBuildError("committed data artifact is stale")
        if (
            generated.manifest_path.read_bytes()
            != committed_manifest.read_bytes()
        ):
            raise ArtifactBuildError("committed manifest artifact is stale")
    return verify_manifest(committed_manifest)
