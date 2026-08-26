"""
Helper utilities for resource path resolution and PyInstaller compatibility.
"""
import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev mode and for PyInstaller / auto-py-to-exe.
    
    Checks in order:
    1. Direct relative path from sys._MEIPASS (bundled) or script directory
    2. Under 'assets/' prefix if relative_path does not already include it
    3. Legacy locations (e.g. imgs/, tables/ directly)
    
    Args:
        relative_path: Relative path to the asset (e.g., 'assets/imgs/kheedluang.ico', 'tables/Addresscleaner_TambonData.xlsx')
        
    Returns:
        Absolute normalized path to the file.
    """
    # Normalize path separators
    normalized_rel = os.path.normpath(relative_path)
    
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Development mode: base directory is project root
        # If this file is in functions/utils/helpers.py, project root is 2 levels up
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_file_dir, "..", ".."))
        base_path = project_root

    # Candidate 1: direct relative path
    candidate = os.path.join(base_path, normalized_rel)
    if os.path.exists(candidate):
        return candidate

    # Candidate 2: check inside assets/ directory if not prefixed
    if not normalized_rel.startswith("assets"):
        candidate_assets = os.path.join(base_path, "assets", normalized_rel)
        if os.path.exists(candidate_assets):
            return candidate_assets

    # Candidate 3: check without assets/ prefix if it was prefixed
    if normalized_rel.startswith("assets" + os.sep) or normalized_rel.startswith("assets/"):
        unprefixed = normalized_rel.split(os.sep, 1)[-1].replace("/", os.sep)
        candidate_unprefixed = os.path.join(base_path, unprefixed)
        if os.path.exists(candidate_unprefixed):
            return candidate_unprefixed

    # Fallback to direct path even if not yet created (e.g., for saving new files)
    return candidate
