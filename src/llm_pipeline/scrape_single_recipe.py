#!/usr/bin/env python3
"""
Quick script to scrape a single recipe from AllRecipes.com

Usage:
    python scrape_single_recipe.py <url>
    
Example:
    python scrape_single_recipe.py https://www.allrecipes.com/recipe/25346/coconut-rice/
"""

import sys
from pathlib import Path

# Add src to path so we can import scraper
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper_v2 import scrape_allrecipes, save_recipe_data


def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_single_recipe.py <allrecipes_url>")
        print("\nExample:")
        print("  python scrape_single_recipe.py https://www.allrecipes.com/recipe/25346/coconut-rice/")
        sys.exit(1)
    
    url = sys.argv[1]
    
    if "allrecipes.com/recipe/" not in url:
        print("Error: URL must be an AllRecipes recipe URL")
        print("Expected format: https://www.allrecipes.com/recipe/<recipe_id>/<recipe-name>/")
        sys.exit(1)
    
    print(f"Scraping recipe from: {url}")
    print("=" * 60)
    
    recipe_data = scrape_allrecipes(url)
    
    if recipe_data:
        print(f"\n✓ Successfully scraped: {recipe_data.get('title', 'Unknown')}")
        print(f"  Recipe ID: {recipe_data.get('recipe_id', 'Unknown')}")
        print(f"  Rating: {recipe_data.get('rating', {}).get('value', 'N/A')} ({recipe_data.get('rating', {}).get('count', 'N/A')} reviews)")
        print(f"  Total reviews extracted: {len(recipe_data.get('reviews', []))}")
        
        # Count reviews with modifications
        reviews_with_mods = [
            r for r in recipe_data.get("reviews", []) 
            if r.get("has_modification")
        ]
        print(f"  Reviews with modifications: {len(reviews_with_mods)}")
        
        # Show a few reviews with modifications
        if reviews_with_mods:
            print("\n  Sample reviews with modifications:")
            for i, review in enumerate(reviews_with_mods[:3], 1):
                print(f"\n    {i}. Rating: {review.get('rating', 'N/A')} stars")
                print(f"       Text: {review.get('text', '')[:150]}...")
        
        # Save the recipe
        filepath = save_recipe_data(recipe_data)
        print(f"\n✓ Saved to: {filepath}")
        print("\nYou can now test this recipe with:")
        print(f"  cd src && uv run python test_pipeline.py single")
        print(f"  (Make sure to update test_pipeline.py to use the new recipe file)")
    else:
        print("✗ Failed to scrape recipe")
        sys.exit(1)


if __name__ == "__main__":
    main()
