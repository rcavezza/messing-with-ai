# Test Suite

This directory contains the test suite for the Recipe Enhancement Platform.

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_edge_cases.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test
uv run pytest tests/test_edge_cases.py::TestMistakenSubstitutionEdgeCase::test_coconut_rice_mistaken_review_not_in_modifications -v
```

## Test Structure

### `test_edge_cases.py`
**Tests for edge cases and special scenarios**

- **TestMistakenSubstitutionEdgeCase**: Tests the main edge case where a review mentions a mistaken substitution
  - Verifies mistaken substitution reviews are NOT flagged as modifications
  - Tests negative sentiment detection in the scraper
  - Ensures the coconut rice mistaken review is correctly filtered
  - Tests that the pipeline excludes mistaken reviews
  - Validates various negative sentiment patterns
  - Ensures positive modifications are still correctly flagged

### `test_scraper.py`
**Tests for the recipe scraper functionality**

- **TestScraperModificationDetection**: Tests the scraper's modification detection
  - Tests positive modification detection
  - Tests negative modification filtering
  - Tests review text extraction

### `test_pipeline.py`
**Tests for the LLM pipeline core functionality**

- **TestRecipeModifier**: Tests recipe modification logic
  - Tests fuzzy string matching (exact, close, and poor matches)
  - Tests replace operations
  - Tests add operations

- **TestTweakExtractor**: Tests modification extraction logic
  - Tests filtering by has_modification flag
  - Tests processing all valid reviews

## Test Fixtures

Located in `conftest.py`:

- `project_root`: Project root directory
- `data_dir`: Data directory path
- `coconut_rice_recipe_data`: Loaded coconut rice recipe JSON
- `coconut_rice_recipe`: Recipe object for coconut rice
- `coconut_rice_reviews`: List of Review objects from coconut rice
- `mistaken_substitution_review`: Review with mistaken substitution (edge case)

## Key Edge Case Test

The main edge case test (`test_coconut_rice_mistaken_review_not_in_modifications`) verifies:

1. The mistaken substitution review exists in the data
2. It has `has_modification=False` (correctly filtered)
3. It has `is_negative_example=True` (correctly marked)
4. It is NOT included in reviews with modifications
5. The pipeline will NOT process it

This ensures the negative sentiment detection continues to work correctly.

## Test Coverage

The test suite covers:
- ✅ Edge case handling (mistaken substitutions)
- ✅ Negative sentiment detection
- ✅ Positive modification detection
- ✅ Recipe modification operations
- ✅ Fuzzy string matching
- ✅ Review filtering logic

## Adding New Tests

When adding new tests:

1. Follow the existing test structure
2. Use descriptive test names that explain what is being tested
3. Use fixtures from `conftest.py` when possible
4. Mock external dependencies (like API keys) appropriately
5. Test both positive and negative cases

Example:
```python
def test_new_feature_works_correctly(self, coconut_rice_recipe: Recipe):
    """Test that new feature works as expected."""
    # Arrange
    # Act
    # Assert
    assert expected_result == actual_result
```
