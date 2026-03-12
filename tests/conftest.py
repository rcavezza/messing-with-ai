"""
Pytest configuration and shared fixtures.
"""

import json
from pathlib import Path

import pytest

from src.llm_pipeline.models import Recipe, Review
from src.llm_pipeline.paths import get_data_directory


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Get the data directory."""
    return project_root / "data"


@pytest.fixture
def coconut_rice_recipe_data(data_dir: Path) -> dict:
    """Load the coconut rice recipe data."""
    recipe_file = data_dir / "recipe_25346_coconut-rice.json"
    with open(recipe_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def coconut_rice_recipe(coconut_rice_recipe_data: dict) -> Recipe:
    """Create a Recipe object from coconut rice data."""
    from src.llm_pipeline.models import Recipe

    return Recipe(
        recipe_id=coconut_rice_recipe_data["recipe_id"],
        title=coconut_rice_recipe_data["title"],
        ingredients=coconut_rice_recipe_data["ingredients"],
        instructions=coconut_rice_recipe_data["instructions"],
        description=coconut_rice_recipe_data.get("description"),
        servings=coconut_rice_recipe_data.get("servings"),
    )


@pytest.fixture
def coconut_rice_reviews(coconut_rice_recipe_data: dict) -> list[Review]:
    """Create Review objects from coconut rice data."""
    reviews = []
    for review_data in coconut_rice_recipe_data.get("reviews", []):
        if review_data.get("text"):
            review = Review(
                text=review_data["text"],
                rating=review_data.get("rating"),
                username=review_data.get("username"),
                has_modification=review_data.get("has_modification", False),
            )
            reviews.append(review)
    return reviews


@pytest.fixture
def mistaken_substitution_review() -> Review:
    """Create a review with a mistaken substitution (edge case)."""
    return Review(
        text="This turned out gluey and stuck to the bottom of the pan and still was absolutely beautiful! However, instead of Coconut milk, I mistakenly used Evaporated milk! Next time I shall use the correct ingredients!",
        rating=4,
        has_modification=False,  # Should be False due to negative sentiment
        username="Zizanie",
    )
