"""Download the Victoria Road Crash Data files from the DTP open data portal.

The portal runs CKAN, so instead of hardcoding file URLs we ask the CKAN API
for the dataset's current resource list. A manifest records what was downloaded
and when, so every analysis can be traced back to a specific data snapshot.

Usage:
    python -m src.extract.download
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

CKAN_API_URL = "https://opendata.transport.vic.gov.au/api/3/action/package_show"
DATASET_ID = "victoria-road-crash-data"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.json"
WANTED_FORMATS = {"CSV", "PDF"}
CHUNK_SIZE = 1024 * 1024
TIMEOUT_SECONDS = 60

logger = logging.getLogger(__name__)


def fetch_resource_list() -> list[dict]:
    response = requests.get(CKAN_API_URL, params={"id": DATASET_ID}, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    resources = response.json()["result"]["resources"]
    return [r for r in resources if r.get("format", "").upper() in WANTED_FORMATS]


def file_name_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    # Write to a temporary file first so an interrupted download never
    # leaves a half-written file that looks complete.
    partial_path = destination.with_suffix(destination.suffix + ".part")
    with requests.get(url, stream=True, timeout=TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        with partial_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                file.write(chunk)
    partial_path.replace(destination)


def is_already_downloaded(destination: Path, expected_size: int | None) -> bool:
    return destination.exists() and expected_size is not None and destination.stat().st_size == expected_size


def download_all() -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for resource in fetch_resource_list():
        file_name = file_name_from_url(resource["url"])
        destination = RAW_DIR / file_name
        expected_size = resource.get("size")

        if is_already_downloaded(destination, expected_size):
            logger.info("Skipping %s (already downloaded, size matches)", file_name)
        else:
            logger.info("Downloading %s ...", file_name)
            download_file(resource["url"], destination)

        manifest.append(
            {
                "name": resource["name"],
                "file_name": file_name,
                "url": resource["url"],
                "source_last_modified": resource.get("last_modified"),
                "bytes": destination.stat().st_size,
                "sha256": sha256_of(destination),
                "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    manifest = download_all()
    total_mb = sum(item["bytes"] for item in manifest) / 1024 / 1024
    logger.info("Done: %d files, %.1f MB, manifest written to %s", len(manifest), total_mb, MANIFEST_PATH)


if __name__ == "__main__":
    main()
