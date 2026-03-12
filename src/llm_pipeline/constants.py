"""
Constants used throughout the LLM pipeline.

This module centralizes all magic numbers and configuration values to improve
code readability and maintainability.
"""

# LLM Configuration
DEFAULT_LLM_MODEL = "gpt-3.5-turbo"
LLM_TEMPERATURE = 0.1  # Low temperature for consistent, deterministic outputs
LLM_MAX_TOKENS = 1000  # Maximum tokens for LLM response
LLM_MAX_RETRIES = 2  # Maximum retry attempts for LLM extraction

# Text Processing
REVIEW_TEXT_PREVIEW_LENGTH = 100  # Characters to show in review previews
RECIPE_TITLE_MAX_LENGTH = 30  # Maximum characters for recipe title in filenames
IMPACT_DESCRIPTIONS_LIMIT = 3  # Maximum number of impact descriptions to include in summary

# Fuzzy Matching
DEFAULT_SIMILARITY_THRESHOLD = 0.6  # Minimum similarity score for fuzzy matching (0-1)
VALIDATION_SIMILARITY_THRESHOLD = 0.8  # Higher threshold for validation checks

# Scraping Configuration
MAX_PHOTO_DIALOG_ITEMS = 10  # Maximum photo dialog items to check for featured reviews
MAX_REVIEW_SELECTOR_RESULTS = 50  # Maximum reviews to find with selector
MAX_REVIEWS_TO_PROCESS = 30  # Maximum reviews to process from HTML
MAX_TITLE_SLUG_LENGTH = 50  # Maximum characters for title slug in filenames
JSON_INDENT_LEVEL = 2  # JSON indentation level for saved files
DEFAULT_SITEMAP_LIMIT = 5  # Default limit for sitemap recipe scraping

# Display/Formatting
LOG_SEPARATOR_LENGTH = 60  # Length of separator line in logs

# Recipe Content Types
TARGET_INGREDIENTS = "ingredients"
TARGET_INSTRUCTIONS = "instructions"

# Edit Operations
OPERATION_REPLACE = "replace"
OPERATION_ADD_AFTER = "add_after"
OPERATION_REMOVE = "remove"

# Change Types
CHANGE_TYPE_INGREDIENT = "ingredient"
CHANGE_TYPE_INSTRUCTION = "instruction"
