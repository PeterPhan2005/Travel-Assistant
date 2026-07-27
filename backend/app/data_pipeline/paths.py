"""Repository-owned curated data paths."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CURATED_DATA_ROOT = REPOSITORY_ROOT / "data" / "curated"
CURATED_SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "schemas"
    / "curated-package-v1.schema.json"
)

CITY_PACKAGE_PATHS = {
    "bkk": CURATED_DATA_ROOT / "bangkok" / "package-v1.yaml",
    "hcmc": CURATED_DATA_ROOT / "hcmc" / "package-v1.yaml",
}
