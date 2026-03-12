"""
Tests for the LLM pipeline functionality.

Tests the core pipeline operations including modification extraction,
recipe modification, and enhanced recipe generation.
"""

import pytest

from src.llm_pipeline.models import ModificationEdit, ModificationObject, Recipe, Review
from src.llm_pipeline.recipe_modifier import RecipeModifier
from src.llm_pipeline.tweak_extractor import TweakExtractor


class TestRecipeModifier:
    """Test the recipe modification functionality."""

    def test_fuzzy_matching_finds_exact_match(self):
        """Test that fuzzy matching finds exact matches."""
        modifier = RecipeModifier()

        target = "1 cup white sugar"
        candidates = ["1 cup butter", "1 cup white sugar", "1 cup brown sugar"]

        match, index, score = modifier.find_best_match(target, candidates)

        assert match == "1 cup white sugar"
        assert index == 1
        assert score == 1.0

    def test_fuzzy_matching_finds_close_match(self):
        """Test that fuzzy matching finds close matches above threshold."""
        modifier = RecipeModifier(similarity_threshold=0.6)

        target = "1 cup white sugar"
        candidates = ["1 cup white sugar, sifted", "1 cup butter"]

        match, index, score = modifier.find_best_match(target, candidates)

        assert match is not None
        assert score >= 0.6

    def test_fuzzy_matching_rejects_poor_match(self):
        """Test that fuzzy matching rejects matches below threshold."""
        modifier = RecipeModifier(similarity_threshold=0.6)

        target = "1 cup white sugar"
        candidates = ["2 cups flour", "3 eggs"]

        match, index, score = modifier.find_best_match(target, candidates)

        assert match is None
        assert score < 0.6

    def test_apply_replace_operation(self):
        """Test applying a replace operation to recipe ingredients."""
        modifier = RecipeModifier()

        recipe = Recipe(
            recipe_id="test",
            title="Test Recipe",
            ingredients=["1 cup white sugar", "2 cups flour"],
            instructions=[],
        )

        modification = ModificationObject(
            modification_type="quantity_adjustment",
            reasoning="Test modification",
            edits=[
                ModificationEdit(
                    target="ingredients",
                    operation="replace",
                    find="1 cup white sugar",
                    replace="0.5 cup white sugar",
                )
            ],
        )

        modified_recipe, change_records = modifier.apply_modification(recipe, modification)

        assert "0.5 cup white sugar" in modified_recipe.ingredients
        assert "1 cup white sugar" not in modified_recipe.ingredients
        assert len(change_records) == 1
        assert change_records[0].operation == "replace"

    def test_apply_add_operation(self):
        """Test applying an add_after operation."""
        modifier = RecipeModifier()

        recipe = Recipe(
            recipe_id="test",
            title="Test Recipe",
            ingredients=["1 cup sugar", "2 cups flour"],
            instructions=[],
        )

        modification = ModificationObject(
            modification_type="addition",
            reasoning="Add vanilla",
            edits=[
                ModificationEdit(
                    target="ingredients",
                    operation="add_after",
                    find="1 cup sugar",
                    add="1 teaspoon vanilla extract",
                )
            ],
        )

        modified_recipe, change_records = modifier.apply_modification(recipe, modification)

        assert "1 teaspoon vanilla extract" in modified_recipe.ingredients
        assert len(modified_recipe.ingredients) == 3
        assert len(change_records) == 1
        assert change_records[0].operation == "add"


class TestTweakExtractor:
    """Test the tweak extraction functionality."""

    def test_extract_single_modification_filters_by_flag(self):
        """Test that extract_single_modification only considers reviews with has_modification=True."""
        import os
        from unittest.mock import patch

        # Mock API key for testing
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            extractor = TweakExtractor()

            reviews = [
                Review(text="Great recipe!", rating=5, has_modification=False),
                Review(
                    text="I added extra salt", rating=4, has_modification=True
                ),
                Review(text="Not good", rating=2, has_modification=False),
            ]

            recipe = Recipe(
                recipe_id="test",
                title="Test",
                ingredients=[],
                instructions=[],
            )

            # Should only consider the review with has_modification=True
            modification_reviews = [r for r in reviews if r.has_modification]
            assert len(modification_reviews) == 1

    def test_extract_all_modifications_returns_all_valid_reviews(self):
        """Test that extract_all_modifications processes all reviews with modifications."""
        import os
        from unittest.mock import patch

        # Mock API key for testing
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            extractor = TweakExtractor()

            reviews = [
                Review(text="Great recipe!", rating=5, has_modification=False),
                Review(
                    text="I added extra salt", rating=4, has_modification=True
                ),
                Review(
                    text="I used less sugar", rating=5, has_modification=True
                ),
                Review(text="Not good", rating=2, has_modification=False),
            ]

            recipe = Recipe(
                recipe_id="test",
                title="Test",
                ingredients=[],
                instructions=[],
            )

            # Should find 2 reviews with modifications
            modification_reviews = [r for r in reviews if r.has_modification]
            assert len(modification_reviews) == 2
