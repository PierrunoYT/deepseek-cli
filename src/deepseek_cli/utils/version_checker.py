"""Version checker for DeepSeek CLI"""

import json
import time
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
from typing import Optional, Tuple

import requests

# How long a PyPI lookup stays fresh. Without this the CLI made a blocking
# network request on every single startup.
CACHE_TTL_SECONDS = 24 * 60 * 60


def get_current_version() -> str:
    """Get the current installed version of deepseek-cli"""
    try:
        return version("deepseek-cli")
    except PackageNotFoundError:
        return "0.0.0"


def get_latest_version() -> Optional[str]:
    """Get the latest version from PyPI with better error handling"""
    try:
        response = requests.get(
            "https://pypi.org/pypi/deepseek-cli/json",
            timeout=2,
            headers={'User-Agent': 'deepseek-cli-version-check'}
        )
        response.raise_for_status()
        latest = response.json()["info"]["version"]
    except (requests.RequestException, ValueError, KeyError, TypeError):
        # RequestException covers transport failures; the rest cover a
        # malformed or unexpected JSON body, which must not crash startup.
        return None
    return latest if isinstance(latest, str) else None


def _read_cache(cache_file: Path, ttl_seconds: int) -> Optional[str]:
    """Return the cached latest-version string, or None if missing/stale."""
    try:
        with open(cache_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None
        checked_at = data.get("checked_at")
        latest = data.get("latest")
        if not isinstance(checked_at, (int, float)) or not isinstance(latest, str):
            return None
        if time.time() - checked_at > ttl_seconds:
            return None
        return latest
    except (OSError, ValueError):
        return None


def _write_cache(cache_file: Path, latest: str) -> None:
    """Best-effort cache write; never raises."""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as fh:
            json.dump({"checked_at": time.time(), "latest": latest}, fh)
    except OSError:
        pass


def check_version(
    cache_file: Optional[Path] = None,
    ttl_seconds: int = CACHE_TTL_SECONDS,
) -> Tuple[bool, str, str]:
    """Check if a new version is available.

    Args:
        cache_file: Optional path used to cache the PyPI result. When given,
            the network is contacted at most once per *ttl_seconds*.
        ttl_seconds: Lifetime of a cached result.

    Returns:
        Tuple[bool, str, str]: (update_available, current_version, latest_version)
    """
    current = get_current_version()

    latest: Optional[str] = None
    if cache_file is not None:
        latest = _read_cache(cache_file, ttl_seconds)

    if latest is None:
        latest = get_latest_version()
        if latest is not None and cache_file is not None:
            _write_cache(cache_file, latest)

    if latest and latest != current:
        return True, current, latest
    return False, current, latest or current
