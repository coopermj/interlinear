#!/usr/bin/env python3
"""Download and extract OpenGNT data from GitHub."""

import os
import requests
import zipfile
from pathlib import Path

# OpenGNT data URL - the main keyed features file with glosses
OPENGNT_URL = "https://raw.githubusercontent.com/eliranwong/OpenGNT/master/OpenGNT_keyedFeatures.csv.zip"
OPENGNT_FILENAME = "OpenGNT_keyedFeatures.csv"

DATA_DIR = Path(__file__).parent.parent / "data"


def download_opengnt(force: bool = False) -> Path:
    """Download OpenGNT CSV data if not already present.

    Args:
        force: If True, download even if file exists

    Returns:
        Path to the CSV file
    """
    csv_path = DATA_DIR / OPENGNT_FILENAME
    zip_path = DATA_DIR / f"{OPENGNT_FILENAME}.zip"

    # Check if already downloaded
    if csv_path.exists() and not force:
        print(f"OpenGNT data already exists at {csv_path}")
        return csv_path

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading OpenGNT data from GitHub...")
    response = requests.get(OPENGNT_URL, stream=True)
    response.raise_for_status()

    # Save zip file
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(DATA_DIR)

    # Clean up zip file
    zip_path.unlink()

    print(f"OpenGNT data saved to {csv_path}")
    return csv_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download OpenGNT data")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    args = parser.parse_args()

    download_opengnt(force=args.force)
