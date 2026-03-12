"""
Tests for the recipe scraper functionality.

Tests the scraper's ability to correctly identify modifications and filter
negative examples.
"""

import pytest

from src.scraper_v2 import extract_review_data


class TestScraperModificationDetection:
    """Test the scraper's modification detection logic."""

    def test_detects_positive_modifications(self):
        """Test that positive modifications are correctly detected."""
        from bs4 import BeautifulSoup

        positive_reviews = [
            "I added an extra egg yolk for chewier texture",
            "I used half a cup of sugar instead of a full cup",
            "I substituted butter for margarine and it was great",
            "Next time I'll definitely make this again",
        ]

        for review_text in positive_reviews:
            # Create a mock BeautifulSoup element
            html = f'<div class="ugc-review"><div class="ugc-review__text">{review_text}</div></div>'
            soup = BeautifulSoup(html, "html.parser")
            review_elem = soup.find("div", class_="ugc-review")

            result = extract_review_data(review_elem)

            assert (
                result.get("has_modification") is True
            ), f"Should detect modification in: {review_text}"

    def test_filters_negative_modifications(self):
        """Test that negative modifications (mistakes) are filtered out."""
        from bs4 import BeautifulSoup

        negative_reviews = [
            "I mistakenly used evaporated milk instead of coconut milk",
            "I tried X but it didn't work well",
            "I used Y but it was a mistake",
            "Next time I'll use the correct ingredients",
        ]

        for review_text in negative_reviews:
            # Create a mock BeautifulSoup element
            html = f'<div class="ugc-review"><div class="ugc-review__text">{review_text}</div></div>'
            soup = BeautifulSoup(html, "html.parser")
            review_elem = soup.find("div", class_="ugc-review")

            result = extract_review_data(review_elem)

            assert (
                result.get("has_modification") is False
            ), f"Should NOT flag negative review: {review_text}"

            assert (
                result.get("is_negative_example") is True
            ), f"Should mark as negative example: {review_text}"

    def test_extracts_review_text_and_detects_modifications(self):
        """Test that review text is extracted and modifications are detected."""
        from bs4 import BeautifulSoup

        review_text = "This recipe was amazing! I added extra salt."
        
        # Create a mock BeautifulSoup element
        html = f'<div class="ugc-review"><div class="ugc-review__text">{review_text}</div></div>'
        soup = BeautifulSoup(html, "html.parser")
        review_elem = soup.find("div", class_="ugc-review")

        result = extract_review_data(review_elem)

        assert result.get("text") == review_text
        assert result.get("has_modification") is True
