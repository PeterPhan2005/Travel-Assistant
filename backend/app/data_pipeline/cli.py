"""Command-line interface for schema, validation, and explicit seeding."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Sequence

from app.data_pipeline.loader import (
    PackageValidationResult,
    load_all_packages,
    load_package,
)
from app.data_pipeline.paths import CITY_PACKAGE_PATHS
from app.data_pipeline.schema import schema_is_current, write_schema


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.data_pipeline",
        description="Offline curated package validation and explicit seeding.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser(
        "validate",
        help="Validate packages without PostgreSQL.",
    )
    validate_target = validate.add_mutually_exclusive_group()
    validate_target.add_argument(
        "--city",
        choices=sorted(CITY_PACKAGE_PATHS),
    )
    validate_target.add_argument("--path", type=Path)

    seed = commands.add_parser(
        "seed",
        help="Validate and seed exactly one package transactionally.",
    )
    seed_target = seed.add_mutually_exclusive_group(required=True)
    seed_target.add_argument(
        "--city",
        choices=sorted(CITY_PACKAGE_PATHS),
    )
    seed_target.add_argument("--path", type=Path)

    schema = commands.add_parser(
        "schema",
        help="Generate or check the committed JSON Schema.",
    )
    schema_action = schema.add_mutually_exclusive_group(required=True)
    schema_action.add_argument("--check", action="store_true")
    schema_action.add_argument("--write", action="store_true")
    return parser


def _print_validation(result: PackageValidationResult) -> int:
    if result.issues:
        for issue in result.issues:
            print(issue.render(), file=sys.stderr)
        print(
            f"validation failed: {len(result.issues)} issue(s)",
            file=sys.stderr,
        )
        return 1
    for loaded in result.packages:
        package = loaded.package
        print(
            "validated "
            f"package={package.package.package_id} "
            f"city={package.package.city_code.value} "
            f"sources={len(package.sources)} "
            f"pois={len(package.pois)} "
            f"menu_items={len(package.menu_items)} "
            f"narrations={len(package.narrations)}"
        )
    return 0


def _selected_path(city: str | None, path: Path | None) -> Path:
    if path is not None:
        return path
    if city is None:
        raise RuntimeError("A city or path is required.")
    return CITY_PACKAGE_PATHS[city]


def _run_seed(path: Path) -> int:
    result = load_package(path)
    validation_exit = _print_validation(result)
    if validation_exit != 0:
        return validation_exit
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.strip():
        print(
            "seed failed: DATABASE_URL is required",
            file=sys.stderr,
        )
        return 2

    from app.data_pipeline.seeder import (  # noqa: PLC0415
        UnsafeSeedTargetError,
        seed_loaded_package,
    )

    try:
        summary = asyncio.run(
            seed_loaded_package(result.packages[0], database_url)
        )
    except UnsafeSeedTargetError as error:
        print(f"seed refused: {error}", file=sys.stderr)
        return 2
    except Exception:
        print(
            "seed failed: package transaction was rolled back",
            file=sys.stderr,
        )
        return 2
    print(
        "seeded "
        f"package={summary.package_id} city={summary.city_code} "
        f"sources={summary.sources} pois={summary.pois} "
        f"poi_source_links={summary.poi_source_links} "
        f"menu_items={summary.menu_items} "
        f"narrations={summary.narrations}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run one deterministic command and return a process exit code."""
    arguments = _parser().parse_args(argv)
    if arguments.command == "validate":
        if arguments.path is not None or arguments.city is not None:
            path = _selected_path(arguments.city, arguments.path)
            return _print_validation(load_package(path))
        return _print_validation(load_all_packages())
    if arguments.command == "schema":
        if arguments.write:
            write_schema()
            print("wrote curated package schema version 1")
            return 0
        if schema_is_current():
            print("curated package schema version 1 is current")
            return 0
        print(
            "schema check failed: regenerate with "
            "'python -m app.data_pipeline schema --write'",
            file=sys.stderr,
        )
        return 1
    path = _selected_path(arguments.city, arguments.path)
    return _run_seed(path)
