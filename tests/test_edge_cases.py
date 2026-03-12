"""
Tests for edge cases in the recipe enhancement pipeline.

This module tests special cases like mistaken substitutions, negative reviews,
and other edge cases that should be handled correctly.
"""

import json
from pathlib import Path

import pytest

from src.llm_pipeline.models import Recipe, Review
from src.llm_pipeline.paths import get_data_directory, get_recipe_file_path
from src.scraper_v2 import extract_review_data


class TestMistakenSubstitutionEdgeCase:
    """Test that mistaken substitution reviews are correctly filtered out."""

    def test_mistaken_substitution_review_not_flagged(
        self, mistaken_substitution_review: Review
    ):
        """
        Test that a review mentioning a mistaken substitution is NOT flagged as a modification.

        This is the edge case from the coconut rice recipe where a user says:
        "I mistakenly used Evaporated milk! Next time I shall use the correct ingredients!"
        """
        # The review should have has_modification=False due to negative sentiment detection
        assert (
            mistaken_substitution_review.has_modification is False
        ), "Mistaken substitution review should NOT be flagged as a modification"

    def test_scraper_detects_negative_sentiment(self):
        """
        Test that the scraper correctly identifies negative sentiment in reviews.

        This ensures the scraper's negative sentiment detection works correctly
        for the mistaken substitution edge case.
        """
        from bs4 import BeautifulSoup

        review_text = (
            "This turned out gluey and stuck to the bottom of the pan and still was absolutely beautiful! "
            "However, instead of Coconut milk, I mistakenly used Evaporated milk! "
            "Next time I shall use the correct ingredients!"
        )

        # Create a mock BeautifulSoup element
        html = f'<div class="ugc-review"><div class="ugc-review__text">{review_text}</div></div>'
        soup = BeautifulSoup(html, "html.parser")
        review_elem = soup.find("div", class_="ugc-review")

        result = extract_review_data(review_elem)

        # The scraper should detect negative sentiment and NOT flag as modification
        assert (
            result.get("has_modification") is False
        ), "Scraper should detect negative sentiment and not flag as modification"

        assert (
            result.get("is_negative_example") is True
        ), "Scraper should mark this as a negative example"

    def test_coconut_rice_mistaken_review_not_in_modifications(
        self, coconut_rice_recipe_data: dict
    ):
        """
        Test that the mistaken substitution review in coconut rice is not included
        in reviews with modifications.

        This is the main edge case test - ensures the review about mistakenly
        using evaporated milk is filtered out.
        """
        reviews = coconut_rice_recipe_data.get("reviews", [])

        # Find the mistaken substitution review
        mistaken_review = None
        for review in reviews:
            if "mistakenly" in review.get("text", "").lower() and "evaporated" in review.get(
                "text", ""
            ).lower():
                mistaken_review = review
                break

        assert mistaken_review is not None, "Mistaken substitution review should exist in data"

        # Verify it's NOT flagged as a modification
        assert (
            mistaken_review.get("has_modification") is False
        ), "Mistaken substitution review should have has_modification=False"

        # Verify it IS marked as negative example
        assert (
            mistaken_review.get("is_negative_example") is True
        ), "Mistaken substitution review should be marked as negative example"

        # Verify it won't be processed by the pipeline
        reviews_with_modifications = [
            r for r in reviews if r.get("has_modification") is True
        ]

        assert (
            mistaken_review not in reviews_with_modifications
        ), "Mistaken substitution review should NOT be in reviews with modifications"

    def test_pipeline_excludes_mistaken_reviews(
        self, coconut_rice_recipe: Recipe, coconut_rice_reviews: list[Review]
    ):
        """
        Test that the pipeline correctly excludes mistaken substitution reviews
        when processing modifications.

        This ensures the pipeline only processes valid, positive modifications.
        """
        from src.llm_pipeline.pipeline import LLMAnalysisPipeline

        # Filter to reviews with modifications
        modification_reviews = [r for r in coconut_rice_reviews if r.has_modification]

        # Verify the mistaken review is NOT in the list
        mistaken_reviews = [
            r
            for r in coconut_rice_reviews
            if "mistakenly" in r.text.lower() and "evaporated" in r.text.lower()
        ]

        for mistaken_review in mistaken_reviews:
            assert (
                mistaken_review not in modification_reviews
            ), f"Mistaken review should not be processed: {mistaken_review.text[:50]}..."

        # Verify we have some valid modifications to process
        assert (
            len(modification_reviews) > 0
        ), "Should have at least some valid modifications to process"

    def test_negative_sentiment_patterns(self):
        """
        Test that various negative sentiment patterns are correctly detected.

        This ensures the scraper's negative sentiment detection is comprehensive.
        """
        from bs4 import BeautifulSoup

        negative_reviews = [
            "I mistakenly used X instead of Y",
            "I used X but it was a mistake",
            "I tried X but it didn't work",
            "Next time I'll use the correct ingredients",
            "I won't do that again",
            "I wouldn't recommend this substitution",
            "I'll stick to the original recipe",
        ]

        for review_text in negative_reviews:
            # Create a mock BeautifulSoup element
            html = f'<div class="ugc-review"><div class="ugc-review__text">{review_text}</div></div>'
            soup = BeautifulSoup(html, "html.parser")
            review_elem = soup.find("div", class_="ugc-review")

            result = extract_review_data(review_elem)

            assert (
                result.get("has_modification") is False
            ), f"Review with negative sentiment should not be flagged: {review_text}"

            assert (
                result.get("is_negative_example") is True
            ), f"Review should be marked as negative example: {review_text}"

    def test_positive_modifications_still_flagged(self):
        """
        Test that positive modifications are still correctly flagged.

        Ensures our negative sentiment detection doesn't break positive cases.
        """
        from bs4 import BeautifulSoup

        positive_reviews = [
            "I added extra coconut milk and it was amazing!",
            "I substituted jasmine rice for basmati and it worked perfectly",
            "I used 2 cups instead of 1 cup and it was much better",
            "Next time I'll definitely make this again with these changes",
        ]

        for review_text in positive_reviews:
            # Create a mock BeautifulSoup element
            html = f'<div class="ugc-review"><div class="ugc-review__text">{review_text}</div></div>'
            soup = BeautifulSoup(html, "html.parser")
            review_elem = soup.find("div", class_="ugc-review")

            result = extract_review_data(review_elem)

            assert (
                result.get("has_modification") is True
            ), f"Positive modification should be flagged: {review_text}"

            assert (
                result.get("is_negative_example") is not True
            ), f"Positive modification should not be negative: {review_text}"
