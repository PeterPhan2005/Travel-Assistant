"""Focused CLI for deterministic travel-package artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.travel_packages.builder import (
    ArtifactBuildError,
    ArtifactVerificationError,
    build_city_package,
    check_committed_artifact,
    verify_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.travel_packages",
        description="Build and verify offline static travel packages.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser(
        "build",
        help="Build exactly one selected city.",
    )
    build.add_argument(
        "--city",
        required=True,
        choices=sorted(CITY_PACKAGE_PATHS),
    )
    build.add_argument("--output-dir", required=True, type=Path)

    verify = commands.add_parser(
        "verify",
        help="Verify one existing manifest and its data file.",
    )
    verify.add_argument("--manifest", required=True, type=Path)

    check = commands.add_parser(
        "check",
        help="Check one committed city artifact for deterministic drift.",
    )
    check.add_argument(
        "--city",
        choices=sorted(CITY_PACKAGE_PATHS),
        default="hcmc",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one artifact command and return a deterministic exit code."""
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "build":
            result = build_city_package(
                arguments.city,
                arguments.output_dir,
            )
            print(
                "built "
                f"package={result.manifest.package_id} "
                f"city={result.manifest.city.value} "
                f"data={result.data_path.name} "
                f"manifest={result.manifest_path.name} "
                f"bytes={result.manifest.byte_size} "
                f"sha256={result.manifest.sha256}"
            )
            return 0
        if arguments.command == "verify":
            verified = verify_manifest(arguments.manifest)
            print(
                "verified "
                f"package={verified.manifest.package_id} "
                f"city={verified.manifest.city.value} "
                f"data={verified.data_path.name} "
                f"bytes={verified.manifest.byte_size} "
                f"sha256={verified.manifest.sha256}"
            )
            return 0
        checked = check_committed_artifact(arguments.city)
        print(
            "current "
            f"package={checked.manifest.package_id} "
            f"city={checked.manifest.city.value} "
            f"data={checked.data_path.name} "
            f"bytes={checked.manifest.byte_size} "
            f"sha256={checked.manifest.sha256}"
        )
        return 0
    except (ArtifactBuildError, ArtifactVerificationError) as error:
        print(f"{arguments.command} failed: {error}", file=sys.stderr)
        return 1
