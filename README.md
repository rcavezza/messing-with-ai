# Recipe Enhancement Platform

Automatically enhances recipes by analyzing and applying community-tested modifications from AllRecipes.com. Uses LLM processing to extract meaningful recipe tweaks and apply them with full citation tracking.

## Project Objectives

The Recipe Enhancement Platform aims to:

1. **Extract Community Wisdom**: Parse user reviews from AllRecipes.com to identify recipe modifications that improve outcomes
2. **Structure Modifications**: Use LLM (GPT-3.5-turbo) to convert natural language review text into structured, actionable recipe changes
3. **Apply Changes Intelligently**: Use fuzzy string matching to accurately apply modifications to original recipes
4. **Provide Full Attribution**: Track every change back to its source review, including rating and reasoning
5. **Handle Edge Cases**: Filter out negative examples (mistaken substitutions) and process multiple modifications per review

### Key Features

- ✅ **Multiple Modifications**: Extracts all discrete modifications from a single review (e.g., "I added an egg and halved the sugar")
- ✅ **Negative Sentiment Detection**: Automatically filters out mistaken substitutions and negative modifications
- ✅ **Flexible Processing**: Process one random review or all reviews with modifications
- ✅ **Full Attribution**: Every modification includes source review, reasoning, and expected impact
- ✅ **Test Coverage**: Comprehensive test suite including edge case handling

## Installation

This project uses [`uv`](https://docs.astral.sh/uv/) for fast, reliable Python package management.

### Prerequisites

- Python 3.13+
- `uv` package manager

### Setup

```bash
# Install dependencies
uv venv
source .venv/bin/activate
uv pip sync pyproject.toml
```

### Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

## Usage

### 1. Scrape Recipes (Optional - data already provided)

```bash
# Scrape all recipes from sitemap
uv run python src/scraper_v2.py

# Scrape a single recipe
python3 scrape_single_recipe.py https://www.allrecipes.com/recipe/25346/coconut-rice/
```

### 2. Run Recipe Enhancement Pipeline

The pipeline can process recipes in several ways:

```bash
# Test default recipe (chocolate chip cookies) - one random review
uv run python src/test_pipeline.py

# Test a specific recipe - one random review
uv run python src/test_pipeline.py recipe_25346_coconut-rice.json

# Test a specific recipe - process ALL reviews with modifications
uv run python src/test_pipeline.py recipe_25346_coconut-rice.json --all-reviews

# Process all recipes - one review per recipe
uv run python src/test_pipeline.py all

# List available recipes
uv run python src/test_pipeline.py list

# Show help
uv run python src/test_pipeline.py help
```

**Processing Modes:**
- **Default (one review)**: Processes one randomly selected review with modifications per recipe
- **`--all-reviews` flag**: Processes ALL reviews with modifications for a specific recipe, applying modifications sequentially

### 3. Run Tests

```bash
# Run entire test suite
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_edge_cases.py -v
uv run pytest tests/test_multiple_modifications.py -v

# Run specific test
uv run pytest tests/test_edge_cases.py::TestMistakenSubstitutionEdgeCase::test_coconut_rice_mistaken_review_not_in_modifications -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## Output

### Enhanced Recipes

Enhanced recipes are saved in `data/enhanced/`:

- `enhanced_[recipe_id]_[recipe-name].json` - Individual enhanced recipes with modifications applied
- `pipeline_summary_report.json` - Summary of all processing results

### Data Structure

Original scraped recipes in `data/` directory contain reviews with `has_modification: true` flags. Enhanced recipes include:

```json
{
  "recipe_id": "10813_enhanced",
  "title": "Best Chocolate Chip Cookies (Community Enhanced)",
  "ingredients": ["1 cup butter", "1 additional egg yolk", ...],
  "modifications_applied": [
    {
      "source_review": {
        "text": "I added an extra egg yolk for chewier texture",
        "rating": 5
      },
      "modification_type": "addition",
      "reasoning": "Improves texture and chewiness",
      "changes_made": [...]
    }
  ],
  "enhancement_summary": {
    "total_changes": 1,
    "change_types": ["addition"],
    "expected_impact": "Chewier texture and improved consistency"
  }
}
```

## How It Works

The LLM Analysis Pipeline processes recipes in 3 steps:

1. **Tweak Extraction**: Uses GPT-3.5-turbo to extract structured modifications from review text. Can extract multiple discrete modifications from a single review (e.g., "I added an egg and halved the sugar" → 2 edits)
2. **Recipe Modification**: Applies changes to the original recipe using fuzzy string matching (similarity threshold: 0.6)
3. **Enhanced Recipe Generation**: Creates enhanced version with full citation tracking back to source review

### Negative Sentiment Detection

The scraper automatically filters out negative modifications:
- Detects patterns like "mistakenly", "didn't work", "next time I'll use correct ingredients"
- Marks these as `is_negative_example: true` and `has_modification: false`
- Prevents mistaken substitutions from being applied

### Multiple Modifications

The system can extract multiple discrete modifications from a single review:
- Example: "I added an egg and halved the sugar" → 2 edits extracted
- All edits are applied sequentially
- Both edits are captured, but categorized under a single `modification_type` (design limitation)

## Project Structure

```
ai-eng-assignment/
├── data/                          # All recipe data
│   ├── enhanced/                 # Enhanced recipe outputs
│   └── recipe_*.json             # Scraped recipe data
├── src/
│   ├── llm_pipeline/             # Core pipeline code
│   │   ├── pipeline.py           # Main orchestrator
│   │   ├── tweak_extractor.py   # LLM modification extraction
│   │   ├── recipe_modifier.py    # Apply modifications
│   │   ├── enhanced_recipe_generator.py  # Generate output
│   │   ├── models.py            # Pydantic data models
│   │   ├── prompts.py           # LLM prompts
│   │   ├── paths.py             # Path management
│   │   └── constants.py         # Centralized constants
│   ├── scraper_v2.py            # Recipe scraper
│   └── test_pipeline.py         # CLI test interface
├── tests/                        # Test suite
│   ├── test_edge_cases.py       # Edge case tests
│   ├── test_multiple_modifications.py  # Multiple edits tests
│   ├── test_pipeline.py         # Pipeline logic tests
│   └── test_scraper.py          # Scraper tests
├── scrape_single_recipe.py      # Single recipe scraper helper
└── README.md                     # This file
```

## Development

```bash
# Add dependencies
uv add <package_name>

# Add dev dependencies
uv add --dev <package_name>

# Run tests
uv run pytest tests/ -v

# Run specific recipe
uv run python src/test_pipeline.py recipe_25346_coconut-rice.json --all-reviews
```

## Next Steps

The following issues and improvements have been identified for future development:

### High Priority

1. **Use All Few-Shot Examples** ⚠️
   - **Issue**: Only 2 of 4 few-shot examples are used (line 170 in `src/llm_pipeline/prompts.py`)
   - **Impact**: Missing 50% of training examples, potentially reducing extraction accuracy
   - **Fix**: Change `FEW_SHOT_EXAMPLES[:2]` to `FEW_SHOT_EXAMPLES[:4]` or implement intelligent example selection
   - **Location**: `src/llm_pipeline/prompts.py:170`

2. **Multiple Modification Types** ⚠️
   - **Issue**: Single `modification_type` per review limits semantic precision
   - **Impact**: Reviews with mixed types (e.g., addition + quantity adjustment) lose precision
   - **Fix**: Consider `modification_types: List[str]` or `"mixed"` type
   - **Location**: `src/llm_pipeline/models.py:32-45`

3. **Configurable Similarity Threshold** ⚠️
   - **Issue**: Fixed 0.6 similarity threshold may not work for all recipes
   - **Impact**: Some recipes might need stricter/looser matching
   - **Fix**: Make threshold configurable per recipe or adaptive based on recipe complexity
   - **Location**: `src/llm_pipeline/constants.py:DEFAULT_SIMILARITY_THRESHOLD`

### Medium Priority

4. **Conflict Detection** ⚠️
   - **Issue**: No detection of conflicting modifications from different reviews
   - **Impact**: Conflicting changes (e.g., "add salt" vs "reduce salt") are applied sequentially, last one wins
   - **Fix**: Detect conflicts and allow user choice or smart resolution
   - **Location**: `src/llm_pipeline/recipe_modifier.py:apply_modifications_batch`

5. **Edit Dependency Validation** ⚠️
   - **Issue**: No validation that edits can be applied in the order specified
   - **Impact**: Edits that depend on each other might fail
   - **Fix**: Validate edit order and dependencies before application
   - **Location**: `src/llm_pipeline/recipe_modifier.py:apply_modification`

6. **Partial Success Handling** ⚠️
   - **Issue**: If one edit fails, the whole modification might fail
   - **Impact**: Partial modifications aren't captured
   - **Fix**: Allow partial success and log which edits succeeded/failed
   - **Location**: `src/llm_pipeline/recipe_modifier.py:apply_edit`

7. **Text Normalization** ⚠️
   - **Issue**: No normalization of recipe text before matching
   - **Impact**: Variations like "1 cup sugar" vs "1 cup granulated sugar" might not match
   - **Fix**: Normalize ingredient names and measurements before fuzzy matching
   - **Location**: `src/llm_pipeline/recipe_modifier.py:find_best_match`

### Low Priority

8. **Expand Modification Types**
   - **Issue**: Only 5 modification types defined
   - **Potential additions**: `cooking_time_adjustment`, `serving_size_adjustment`, `equipment_change`
   - **Location**: `src/llm_pipeline/models.py:35-41`

9. **Better Error Messages**
   - **Issue**: Some error messages could be more descriptive
   - **Fix**: Improve error handling and user-facing messages
   - **Location**: Throughout pipeline code

10. **Performance Optimization**
    - **Issue**: Processing all reviews can be slow for recipes with many reviews
    - **Fix**: Add progress indicators, parallel processing, or batching
    - **Location**: `src/llm_pipeline/pipeline.py:_process_all_reviews`

### Documentation

- ✅ Test suite created with edge case coverage
- ✅ Scalability analysis documented (`docs/SCALABILITY_ANALYSIS.md`)
- ✅ Multiple modifications analysis documented (`docs/MULTIPLE_MODIFICATIONS_ANSWER.md`)
- ✅ Edge case analysis documented (`docs/EDGE_CASE_ANALYSIS.md`)

### Testing Gaps

Consider adding tests for:
- End-to-end pipeline execution (requires API key)
- Conflicting modifications handling
- Edit dependency scenarios
- Very long recipes/reviews
- Performance under load

## Additional Documentation

All documentation files are located in the `docs/` directory:

- `docs/HOW_IT_WORKS.md` - Deep dive into pipeline execution
- `docs/EDGE_CASE_ANALYSIS.md` - Analysis of mistaken substitution edge case
- `docs/SCALABILITY_ANALYSIS.md` - Detailed scalability and assumption analysis
- `docs/MULTIPLE_MODIFICATIONS_ANSWER.md` - Answers to multiple modifications questions
- `docs/REFACTORING_SUMMARY.md` - Summary of code quality improvements
- `docs/JUNIOR_ENGINEER_EXPLANATION.md` - Explanation of original code structure
- `tests/README.md` - Test suite documentation


# Thoughts from Bobby - unrelated to README

# Assumptions

First assumption is that we only want positive sentiment updates to recipes. I don't see why we would want to do ANY substitution, for example, one that made the recipe worse.

# Things noticed

1.) I searched allrecipes.com for "instead" and immediately found a use case that may be missed where there is a mistake the user made, but still might be considered an "enhancement" mistakenly.

2.) Originally, there was no easy way to figure out exactly what the "all" and "one" things were doing. I naively assumed they were getting only 1 or everything in some type of order or randomness. It took Cursor explaining to me that "one" would get the cookies every time. 

3.) I had the LLM take a look at make changes to issues the junior engineer might have left in there. I let the LLM take over and make necessary tweaks there while I still don't have a full understanding of hte code base and what's happening. 

4.) I had the LLM take care of key refactors including the following: 

-Make single accept a recipe file argument
-Fix the path inconsistencies
-Make it work from any directory
-Add better command-line options

I can't take a ton of credit here as the LLM did the legwork and I read through its suggestions after I told it hte context of the junior engineer and it quickly did some refactors and upgrades. I WILL take credit for trying to get the LLM to write best practices code due to some prompting. 

5.) I had the LLM make an additional enhancement of adding a qualifier in the command line tools to make the LLM perform all enhancements when going through a specific recipe. For example, this command is now a reality...

`uv run python src/test_pipeline.py recipe_25346_coconut-rice.json --all-reviews`

6.) I had the LLM fix the issue of sentiment issues when looking at reviews. That's probably a major issue that would cause issues with user experience in the end application. 

7.) I had the LLM make a simple test suite so that we can have some semblance of things not breaking as we move forward. 

# Problem analysis and solution approach

1.) Analysis of the problem was fairly difficult as the goal of the application as a whole was unclear. My best guess was that we ultimately want to build something that will scrape EVERYTHING from that website. That can be pushed to a later point in time; however, because we need to get the kinks out of the individual reviews first. 

2.) Understanding what is in the codebase was the first objective. I relied heavily on the LLM after some of the api contracts w/ the command line didn't make intuitive sense to me. test_pipeline all and test_pipeline one were confusing. It took a while to get a full sense of what was happening. When I fed the LLM the context of the junior engineer building the first version, it immediately picked up on the clues and I was able to get an understanding of what was there and the key goals of the application. 

3.) The major goal was understandability and slight improvements. I knew I wouldn't get to do everything I would want to - I also didn't want to put too much time into a one off project that won't get continued to be enhanced. Considering the possibilities, I assumed the worse case scenario fro the application is suggesting alterations that make a recipe worse. Out of all possible issues, this is the only one that makes a user's experience subjectively WORSE.

# Technical Decisions

There weren't many technical decisions here. I'll list a few I think may be pertinent. 

1.) Sentiment analysis to get rid of the improper substitutions problems. 

2.) Refactoring some of the command line tools so they make more intuitive sense.

3.) Being able to easily extract a particular recipe so that it is easier to find and test edge cases quickly. 

4.) Get rid of magic numbers (just makes it easier to read code sometimes and difficult to get that wrong with an LLM)

5.) Add test cases. They're probably not great and I didn't audit them, but some tests are always better than zero tests. 

6.) updating of where data is stored. We don't want data or enhanced data getting into the /src folder. 

# Implementation details and challenges overcome

These should be littered over this document. I don't think I need to elaborate, but the key things were figuring out the original command line commands and what they were exactly doing. 

# Future Improvements

See next steps section.