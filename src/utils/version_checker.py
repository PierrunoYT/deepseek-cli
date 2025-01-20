"""Version checker for DeepSeek CLI"""

import requests
import pkg_resources
from typing import Optional, Tuple

def get_current_version() -> str:
    """Get the current installed version of deepseek-cli"""
    try:
        return pkg_resources.get_distribution("deepseek-cli").version
    except pkg_resources.DistributionNotFound:
        return "0.0.0"

def get_latest_version() -> Optional[str]:
    """Get the latest version from PyPI"""
    try:
        response = requests.get("https://pypi.org/pypi/deepseek-cli/json", timeout=2)
        if response.status_code == 200:
            return response.json()["info"]["version"]
        return None
    except Exception:
        return None

def check_version() -> Tuple[bool, str, str]:
    """Check if a new version is available
    Returns:
        Tuple[bool, str, str]: (update_available, current_version, latest_version)
    """
    current = get_current_version()
    latest = get_latest_version()
    
    if latest and latest != current:
        return True, current, latest
    return False, current, latest or current 