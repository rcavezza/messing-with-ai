# Edge Case Analysis: Mistaken Substitutions

## The Problem

You found a review on [Coconut Rice recipe](https://www.allrecipes.com/recipe/25346/coconut-rice/) where a user mentions making a substitution that was actually a **mistake**, and they want to use the correct ingredients next time.

**Question**: How would the current codebase handle this edge case?

---

## Current Code Behavior

### Step 1: Scraper Detection (`scraper_v2.py:76-92`)

The scraper uses regex patterns to detect if a review contains modifications:

```python
tweak_patterns = [
    r"I (added|used|substituted|replaced|made with|changed)",
    r"(instead of|rather than|in place of)",
    r"(next time|will make again|definitely make)",  # ← This would match!
    r"(doubled|tripled|halved|increased|decreased)",
    r"(more|less|extra) ([\w\s]+)",
]
```

**Example Review** (hypothetical):
> "I substituted jasmine rice for basmati rice, but it didn't work well. Next time I'll use the correct ingredients from the recipe."

**What Happens**:
- ✅ Pattern `r"I (added|used|substituted|replaced|made with|changed)"` matches "I substituted"
- ✅ Pattern `r"(next time|will make again|definitely make)"` matches "Next time"
- **Result**: `has_modification = True` ✅

**Problem**: The scraper flags this as a modification, even though the user is saying the substitution was a **mistake**.

---

### Step 2: LLM Extraction (`tweak_extractor.py:36-111`)

The LLM receives the review text and is asked to extract modifications:

**Current Prompt** (`prompts.py:195-225`):
```
You are an expert recipe analyst. Your job is to extract structured recipe modifications from user reviews.

When a user shares their experience modifying a recipe, you need to:
1. Identify exactly what changes they made
2. Understand why they made those changes
3. Convert their modifications into structured edit operations

[...]

User Review: "I substituted jasmine rice for basmati rice, but it didn't work well. Next time I'll use the correct ingredients from the recipe."

Extract the recipe modifications from this review. The user has made changes to improve the recipe.
```

**What the LLM Might Do**:

**Scenario A: LLM Misinterprets (Likely)**
```json
{
  "modification_type": "ingredient_substitution",
  "reasoning": "User substituted jasmine rice for basmati rice",
  "edits": [
    {
      "target": "ingredients",
      "operation": "replace",
      "find": "basmati rice",
      "replace": "jasmine rice"
    }
  ]
}
```
❌ **Problem**: This would apply the WRONG substitution (the mistake)!

**Scenario B: LLM Correctly Interprets (Possible)**
```json
{
  "modification_type": "removal",
  "reasoning": "User tried substitution but it didn't work, recommends using original recipe",
  "edits": []  // No edits - keep original
}
```
✅ **Better**: But still not ideal - the LLM might not extract the "correct" version.

**Scenario C: LLM Ignores Negative Reviews (Best Case)**
The LLM might recognize negative language ("didn't work well", "mistake") and return:
- Empty edits array
- Or fail validation
- Or return `None`

---

## Current Limitations

### 1. **No Sentiment Analysis**
The scraper doesn't distinguish between:
- ✅ Positive modifications: "I substituted X for Y and it was amazing!"
- ❌ Negative modifications: "I substituted X for Y but it was a mistake"

### 2. **No Context Understanding**
The prompt says "The user has made changes to **improve** the recipe" but doesn't handle cases where:
- The user tried something that didn't work
- The user wants to revert to original
- The user is warning others not to make the same mistake

### 3. **No Negative Signal Detection**
The code doesn't look for negative indicators like:
- "didn't work"
- "mistake"
- "won't do that again"
- "use original"
- "stick to recipe"

---

## How to Test This Edge Case

### Step 1: Scrape the Recipe

```bash
# Use the new helper script
python scrape_single_recipe.py https://www.allrecipes.com/recipe/25346/coconut-rice/
```

This will:
1. Scrape the recipe and all reviews
2. Flag reviews with modifications (including the mistaken one)
3. Save to `data/recipe_25346_coconut-rice.json`

### Step 2: Inspect the Scraped Data

Check if the mistaken substitution review was flagged:

```bash
# Look at the reviews
cat data/recipe_25346_coconut-rice.json | jq '.reviews[] | select(.has_modification == true) | {text: .text, rating: .rating}'
```

### Step 3: Test with Pipeline

Modify `test_pipeline.py` to use the new recipe:

```python
recipe_file = "../data/recipe_25346_coconut-rice.json"
```

Then run:
```bash
cd src && uv run python test_pipeline.py single
```

### Step 4: Check the Result

Look at the enhanced recipe to see:
1. Did the LLM extract the mistaken substitution?
2. Or did it correctly ignore/negate it?
3. What reasoning did it provide?

---

## Potential Solutions

### Option 1: Improve Scraper Detection (Quick Fix)

Add negative sentiment detection to the scraper:

```python
# In scraper_v2.py:extract_review_data()

# Negative patterns that indicate a modification was a mistake
negative_patterns = [
    r"(didn't work|didn't turn out|wasn't good|was a mistake)",
    r"(won't do that|wouldn't recommend|stick to|use original)",
    r"(next time I'll use|next time I'll stick to|next time I'll follow)",
]

has_negative_sentiment = any(
    re.search(pattern, review_data["text"], re.IGNORECASE)
    for pattern in negative_patterns
)

if has_negative_sentiment:
    review_data["has_modification"] = False  # Don't flag as modification
    review_data["is_negative_example"] = True  # Flag for potential filtering
```

### Option 2: Improve LLM Prompt (Better Solution)

Update the prompt to handle negative cases:

```python
SYSTEM_PROMPT = """You are an expert recipe analyst...

IMPORTANT: Some reviews mention modifications that were MISTAKES or didn't work.
- If a user says "I substituted X for Y but it didn't work" → DO NOT extract that substitution
- If a user says "Next time I'll use the original" → Return empty edits array
- If a user warns against a modification → Return empty edits array
- Only extract modifications that the user RECOMMENDS or that IMPROVED the recipe

Look for negative indicators:
- "didn't work", "wasn't good", "mistake", "won't do that again"
- "stick to original", "use recipe as written", "follow the recipe"
"""
```

### Option 3: Post-Processing Filter (Robust Solution)

Add a validation step after LLM extraction:

```python
def validate_modification_sentiment(
    modification: ModificationObject,
    source_review: Review
) -> bool:
    """Check if modification should be applied based on review sentiment."""
    
    negative_indicators = [
        "didn't work", "wasn't good", "mistake", "won't do",
        "stick to", "use original", "follow recipe"
    ]
    
    review_lower = source_review.text.lower()
    
    # If review contains negative indicators, don't apply
    if any(indicator in review_lower for indicator in negative_indicators):
        return False
    
    return True
```

---

## Recommended Approach

**Immediate**: Test the current code with the coconut rice recipe to see what happens.

**Short-term**: Add negative sentiment detection to the scraper (Option 1).

**Long-term**: Improve the LLM prompt and add post-processing validation (Options 2 + 3).

---

## Testing Checklist

- [ ] Scrape the coconut rice recipe
- [ ] Check if mistaken substitution review is flagged
- [ ] Run pipeline on the recipe
- [ ] Inspect enhanced recipe output
- [ ] Document what the LLM extracted
- [ ] Determine if it's a bug or acceptable behavior
- [ ] Implement fix if needed

---

## Code References

- **Scraper Detection**: `src/scraper_v2.py:76-92`
- **LLM Prompt**: `src/llm_pipeline/prompts.py:8-29`
- **LLM Extraction**: `src/llm_pipeline/tweak_extractor.py:36-111`
- **Helper Script**: `scrape_single_recipe.py` (newly created)
