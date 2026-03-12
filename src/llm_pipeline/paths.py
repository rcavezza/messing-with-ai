"""
Path utilities for consistent file and directory handling.

This module provides centralized path management to ensure all paths are
resolved relative to the project root, regardless of where the script is executed.
"""

from pathlib import Path

# Get project root (parent of src/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Standard directories
DATA_DIR = _PROJECT_ROOT / "data"
ENHANCED_DIR = DATA_DIR / "enhanced"

# Ensure directories exist
ENHANCED_DIR.mkdir(parents=True, exist_ok=True)


def get_recipe_file_path(recipe_filename: str) -> Path:
    """
    Get the full path to a recipe file.
    
    Args:
        recipe_filename: Name of recipe file (e.g., "recipe_10813_*.json" or full path)
    
    Returns:
        Path to the recipe file
    
    Raises:
        FileNotFoundError: If recipe file doesn't exist
    """
    recipe_path = Path(recipe_filename)
    
    # If it's already an absolute path or exists as-is, use it
    if recipe_path.is_absolute() or recipe_path.exists():
        if not recipe_path.exists():
            raise FileNotFoundError(f"Recipe file not found: {recipe_path}")
        return recipe_path
    
    # Otherwise, look in data directory
    recipe_path = DATA_DIR / recipe_filename
    
    if not recipe_path.exists():
        raise FileNotFoundError(
            f"Recipe file not found: {recipe_path}\n"
            f"Available recipes in {DATA_DIR}: {list(DATA_DIR.glob('recipe_*.json'))}"
        )
    
    return recipe_path


def get_data_directory() -> Path:
    """Get the data directory path."""
    return DATA_DIR


def get_enhanced_directory() -> Path:
    """Get the enhanced recipes output directory path."""
    return ENHANCED_DIR


def find_all_recipe_files() -> list[Path]:
    """
    Find all recipe files in the data directory.
    
    Returns:
        List of paths to recipe JSON files
    """
    return sorted(DATA_DIR.glob("recipe_*.json"))
