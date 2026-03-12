import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# Constants for scraping configuration
MAX_PHOTO_DIALOG_ITEMS = 10
MAX_REVIEW_SELECTOR_RESULTS = 50
MAX_REVIEWS_TO_PROCESS = 30
MAX_TITLE_SLUG_LENGTH = 50
JSON_INDENT_LEVEL = 2
DEFAULT_SITEMAP_LIMIT = 5
LOG_SEPARATOR_LENGTH = 60


def extract_review_data(review_elem) -> Dict:
    """Extract review/tweak data from a review element"""
    review_data = {}

    # Try to extract review text - updated selectors based on actual HTML
    text_selectors = [
        ("div", {"class": "ugc-review__text"}),
        ("div", {"class": re.compile(r"ugc-review__text")}),
        ("div", {"class": re.compile(r"recipe-review__text")}),
        ("div", {"class": re.compile(r"ReviewText")}),
        ("div", {"class": re.compile(r"ugc-review-body")}),
        ("p", {"class": re.compile(r"review")}),
    ]

    for tag, attrs in text_selectors:
        text_elem = review_elem.find(tag, attrs)
        if text_elem:
            review_text = text_elem.get_text(strip=True)
            if review_text:
                review_data["text"] = review_text
                break

    # Try to extract rating
    rating_selectors = [
        ("div", {"class": "ugc-review__rating"}),
        ("div", {"class": re.compile(r"ugc-review__rating")}),
        ("span", {"class": re.compile(r"rating-stars")}),
        ("div", {"class": re.compile(r"RatingStar")}),
        ("span", {"aria-label": re.compile(r"rated \d+ out of 5")}),
    ]

    for tag, attrs in rating_selectors:
        rating_elem = review_elem.find(tag, attrs)
        if rating_elem:
            # Try to extract number from aria-label or count stars
            aria_label = rating_elem.get("aria-label", "")
            rating_match = re.search(r"rated (\d+)", aria_label)
            if rating_match:
                review_data["rating"] = int(rating_match.group(1))
            else:
                # Count filled stars (SVG elements with class icon-star)
                stars = rating_elem.find_all("svg", {"class": "icon-star"})
                if stars:
                    review_data["rating"] = len(stars)
            break

    # Try to extract username
    user_selectors = [
        ("span", {"class": re.compile(r"recipe-review__author")}),
        ("span", {"class": re.compile(r"reviewer-name")}),
        ("a", {"class": re.compile(r"cook-name")}),
    ]

    for tag, attrs in user_selectors:
        user_elem = review_elem.find(tag, attrs)
        if user_elem:
            review_data["username"] = user_elem.get_text(strip=True)
            break

    # Try to extract date
    date_elem = review_elem.find(
        ["span", "time"], {"class": re.compile(r"recipe-review__date")}
    )
    if date_elem:
        review_data["date"] = date_elem.get_text(strip=True)

    # Look for modifications/tweaks in review text
    if review_data.get("text"):
        review_text = review_data["text"]
        
        # First check for negative indicators that suggest a modification was a mistake
        negative_indicators = [
            r"mistakenly",
            r"was a mistake",
            r"didn't work",
            r"didn't turn out",
            r"wasn't good",
            r"won't do that",
            r"wouldn't recommend",
            r"next time.*correct",
            r"next time.*original",
            r"next time.*recipe as written",
            r"use.*correct ingredients",
            r"stick to.*original",
            r"follow.*recipe",
        ]
        
        has_negative_sentiment = any(
            re.search(pattern, review_text, re.IGNORECASE)
            for pattern in negative_indicators
        )
        
        # If review has negative sentiment, don't flag as modification
        if has_negative_sentiment:
            review_data["has_modification"] = False
            review_data["is_negative_example"] = True
        else:
            # Common patterns for recipe modifications
            tweak_patterns = [
                r"I (added|used|substituted|replaced|made with|changed)",
                r"(instead of|rather than|in place of)",
                r"(next time|will make again|definitely make)",
                r"(doubled|tripled|halved|increased|decreased)",
                r"(more|less|extra) ([\w\s]+)",
            ]

            for pattern in tweak_patterns:
                if re.search(pattern, review_text, re.IGNORECASE):
                    review_data["has_modification"] = True
                    break

    return review_data


def extract_recipe_from_json_ld(data: Any) -> Optional[Dict]:
    """Extract recipe data from various JSON-LD formats"""
    # If it's a dict with @type
    if isinstance(data, dict):
        types = data.get("@type", [])
        # Handle multiple types
        if isinstance(types, list) and "Recipe" in types:
            return data
        elif types == "Recipe":
            return data

    # If it's an array
    elif isinstance(data, list):
        for item in data:
            recipe = extract_recipe_from_json_ld(item)
            if recipe:
                return recipe

    return None


def scrape_allrecipes(url: str) -> Optional[Dict]:
    """
    Scrape recipe data from an AllRecipes URL.

    Args:
        url: AllRecipes recipe URL

    Returns:
        Dictionary containing recipe data or None if scraping fails
    """
    try:
        # Send request with headers to avoid blocking
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Extract recipe data
        recipe_data = {
            "url": url,
            "scraped_at": datetime.now().isoformat(),
        }

        # Get recipe ID from URL
        url_parts = url.split("/")
        for i, part in enumerate(url_parts):
            if part == "recipe" and i + 1 < len(url_parts):
                recipe_data["recipe_id"] = url_parts[i + 1]
                break

        # Get recipe title from H1 if available
        title_element = soup.find("h1")
        if title_element:
            recipe_data["title"] = title_element.text.strip()

        # Look for JSON-LD structured data
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        recipe_found = None
        reviews_from_json_ld = []

        for json_ld in json_ld_scripts:
            try:
                structured_data = json.loads(json_ld.string)
                
                # Check for reviews in JSON-LD
                if isinstance(structured_data, dict):
                    if "review" in structured_data:
                        reviews_from_json_ld.extend(
                            structured_data["review"] if isinstance(structured_data["review"], list) 
                            else [structured_data["review"]]
                        )
                elif isinstance(structured_data, list):
                    for item in structured_data:
                        if isinstance(item, dict):
                            if "review" in item:
                                reviews_from_json_ld.extend(
                                    item["review"] if isinstance(item["review"], list)
                                    else [item["review"]]
                                )
                
                recipe_found = extract_recipe_from_json_ld(structured_data)
                if recipe_found:
                    break
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON-LD: {e}")
                continue

        # Extract from structured data if found
        if recipe_found:
            # Title and description
            recipe_data["title"] = recipe_found.get(
                "name", recipe_data.get("title", "")
            )
            recipe_data["description"] = recipe_found.get("description", "")

            # Ratings
            if "aggregateRating" in recipe_found:
                recipe_data["rating"] = {
                    "value": recipe_found["aggregateRating"].get("ratingValue"),
                    "count": recipe_found["aggregateRating"].get(
                        "ratingCount"
                    ),  # Use ratingCount instead of reviewCount
                }

            # Times
            for time_field in ["prepTime", "cookTime", "totalTime"]:
                if time_field in recipe_found:
                    recipe_data[time_field.lower()] = recipe_found[time_field]

            # Servings/Yield
            recipe_yield = recipe_found.get("recipeYield")
            if recipe_yield:
                if isinstance(recipe_yield, list):
                    recipe_data["servings"] = recipe_yield[0]
                else:
                    recipe_data["servings"] = str(recipe_yield)

            # Ingredients
            ingredients = recipe_found.get("recipeIngredient", [])
            if ingredients:
                recipe_data["ingredients"] = ingredients

            # Instructions
            instructions = recipe_found.get("recipeInstructions", [])
            if instructions:
                recipe_data["instructions"] = []
                for inst in instructions:
                    if isinstance(inst, dict):
                        text = inst.get("text", inst.get("name", ""))
                        if text:
                            recipe_data["instructions"].append(text)
                    elif isinstance(inst, str):
                        recipe_data["instructions"].append(inst)

            # Nutrition
            if "nutrition" in recipe_found:
                recipe_data["nutrition"] = recipe_found["nutrition"]

            # Author
            author = recipe_found.get("author")
            if author:
                if isinstance(author, dict):
                    recipe_data["author"] = author.get("name", str(author))
                else:
                    recipe_data["author"] = str(author)

            # Categories/Keywords
            recipe_data["categories"] = recipe_found.get("recipeCategory", [])
            if "keywords" in recipe_found:
                keywords = recipe_found["keywords"]
                if isinstance(keywords, str):
                    recipe_data["keywords"] = [k.strip() for k in keywords.split(",")]
                else:
                    recipe_data["keywords"] = keywords

        # Extract featured tweaks first - looking for top reviews with photos
        recipe_data["featured_tweaks"] = []

        # Look for photo dialog items which often contain featured reviews
        photo_dialog_items = soup.find_all(
            "div", {"class": re.compile(r"photo-dialog__item")}
        )

        if photo_dialog_items:
            potential_tweaks = []
            for item in photo_dialog_items[:MAX_PHOTO_DIALOG_ITEMS]:
                # Extract review from within the photo dialog item
                review_section = item.find("div", {"class": "ugc-review"})
                if review_section:
                    tweak_data = extract_review_data(review_section)
                    if (
                        tweak_data
                        and tweak_data.get("text")
                        and tweak_data.get("has_modification")
                    ):
                        tweak_data["is_featured"] = True
                        potential_tweaks.append(tweak_data)

            # Take the tweaks as-is without sorting by helpful count
            recipe_data["featured_tweaks"] = potential_tweaks

            if recipe_data["featured_tweaks"]:
                print(
                    f"Extracted {len(recipe_data['featured_tweaks'])} featured tweaks from photo reviews"
                )

        # Extract reviews/comments for tweaks (updated selectors)
        recipe_data["reviews"] = []

        # Try different review selectors - prioritize ugc-review which is the current class
        review_selectors = [
            ("div", {"class": "ugc-review"}),  # Exact match first
            ("div", {"class": re.compile(r"ugc-review")}),  # Then regex
            ("div", {"class": re.compile(r"ReviewCard__container")}),
            ("div", {"class": re.compile(r"review-container")}),
            ("article", {"class": re.compile(r"review")}),
        ]

        reviews_found = []
        for tag, attrs in review_selectors:
            reviews_found = soup.find_all(
                tag, attrs, limit=MAX_REVIEW_SELECTOR_RESULTS
            )
            if reviews_found:
                print(
                    f"Found {len(reviews_found)} reviews using selector: {tag} {attrs}"
                )
                break

        # Parse reviews using the helper function
        for review_elem in reviews_found[:MAX_REVIEWS_TO_PROCESS]:
            review_data = extract_review_data(review_elem)
            if review_data and review_data.get("text"):
                recipe_data["reviews"].append(review_data)

        # Also extract reviews from JSON-LD structured data
        for json_review in reviews_from_json_ld:
            if isinstance(json_review, dict):
                review_data = {
                    "text": json_review.get("reviewBody", ""),
                    "rating": int(json_review.get("reviewRating", {}).get("ratingValue", 0)) if json_review.get("reviewRating") else None,
                }
                
                # Extract author name
                author = json_review.get("author", {})
                if isinstance(author, dict):
                    review_data["username"] = author.get("name")
                elif isinstance(author, str):
                    review_data["username"] = author
                
                # Extract date if available
                if "datePublished" in json_review:
                    review_data["date"] = json_review["datePublished"]
                
                # Check for modifications in review text (using same logic as HTML reviews)
                if review_data.get("text"):
                    review_text = review_data["text"]
                    
                    # Check for negative indicators first
                    negative_indicators = [
                        r"mistakenly",
                        r"was a mistake",
                        r"didn't work",
                        r"didn't turn out",
                        r"wasn't good",
                        r"won't do that",
                        r"wouldn't recommend",
                        r"next time.*correct",
                        r"next time.*original",
                        r"next time.*recipe as written",
                        r"use.*correct ingredients",
                        r"stick to.*original",
                        r"follow.*recipe",
                    ]
                    
                    has_negative_sentiment = any(
                        re.search(pattern, review_text, re.IGNORECASE)
                        for pattern in negative_indicators
                    )
                    
                    if has_negative_sentiment:
                        review_data["has_modification"] = False
                        review_data["is_negative_example"] = True
                    else:
                        tweak_patterns = [
                            r"I (added|used|substituted|replaced|made with|changed)",
                            r"(instead of|rather than|in place of)",
                            r"(next time|will make again|definitely make)",
                            r"(doubled|tripled|halved|increased|decreased)",
                            r"(more|less|extra) ([\w\s]+)",
                        ]
                        
                        for pattern in tweak_patterns:
                            if re.search(pattern, review_text, re.IGNORECASE):
                                review_data["has_modification"] = True
                                break
                
                if review_data.get("text"):
                    recipe_data["reviews"].append(review_data)

        print(f"Extracted {len(recipe_data['reviews'])} reviews ({len(reviews_from_json_ld)} from JSON-LD)")

        return recipe_data

    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def save_recipe_data(recipe_data: Dict, filename: str = None) -> str:
    """
    Save recipe data to a JSON file.

    Args:
        recipe_data: Dictionary containing recipe data
        filename: Optional filename, defaults to recipe_id.json

    Returns:
        Path to saved file
    """
    if filename is None:
        recipe_id = recipe_data.get("recipe_id", "unknown")
        title_slug = re.sub(r"[^a-z0-9]+", "-", recipe_data.get("title", "").lower())[
            :MAX_TITLE_SLUG_LENGTH
        ]
        filename = f"data/recipe_{recipe_id}_{title_slug}.json"

    # Create data directory if it doesn't exist
    import os

    os.makedirs("data", exist_ok=True)

    filepath = filename if "/" in filename else f"data/{filename}"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(recipe_data, f, indent=JSON_INDENT_LEVEL, ensure_ascii=False)

    print(f"Saved recipe data to {filepath}")
    return filepath


def scrape_sitemap_recipes(limit: int = DEFAULT_SITEMAP_LIMIT) -> List[str]:
    """
    Scrape recipe URLs from AllRecipes sitemap

    Args:
        limit: Maximum number of recipe URLs to return

    Returns:
        List of recipe URLs
    """
    sitemap_url = "https://www.allrecipes.com/sitemap_1.xml"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(sitemap_url, headers=headers)
        response.raise_for_status()

        # Parse XML to find recipe URLs
        soup = BeautifulSoup(response.content, "xml")
        urls = []

        for loc in soup.find_all("loc"):
            url = loc.text
            if "/recipe/" in url and url not in urls:
                urls.append(url)
                if len(urls) >= limit:
                    break

        return urls

    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        # Fallback to hardcoded popular recipes
        return [
            "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/",
            "https://www.allrecipes.com/recipe/11679/homemade-mac-and-cheese/",
            "https://www.allrecipes.com/recipe/23600/worlds-best-lasagna/",
            "https://www.allrecipes.com/recipe/24059/creamy-rice-pudding/",
            "https://www.allrecipes.com/recipe/20144/banana-banana-bread/",
        ][:limit]


def main():
    """
    Main function to demonstrate scraping functionality.
    """
    import os

    os.makedirs("data", exist_ok=True)

    # Test with a single recipe first
    test_url = "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/"

    print(f"Testing with: {test_url}")
    print("=" * LOG_SEPARATOR_LENGTH)

    recipe_data = scrape_allrecipes(test_url)

    if recipe_data:
        print(f"\n✓ Successfully scraped: {recipe_data.get('title', 'Unknown')}")
        print(
            f"  Rating: {recipe_data.get('rating', {}).get('value')} ({recipe_data.get('rating', {}).get('count')} reviews)"
        )
        print(f"  Reviews extracted: {len(recipe_data.get('reviews', []))}")
        print(f"  Has ingredients: {'ingredients' in recipe_data}")
        print(f"  Has instructions: {'instructions' in recipe_data}")

        # Count reviews with modifications
        reviews_with_mods = [
            r for r in recipe_data.get("reviews", []) if r.get("has_modification")
        ]
        print(f"  Reviews with modifications: {len(reviews_with_mods)}")

        save_recipe_data(recipe_data)
    else:
        print("✗ Failed to scrape recipe")

    # Now try to get more recipes
    print("\n" + "=" * LOG_SEPARATOR_LENGTH)
    print("Fetching more recipe URLs...")

    recipe_urls = scrape_sitemap_recipes(limit=DEFAULT_SITEMAP_LIMIT)
    print(f"Found {len(recipe_urls)} recipe URLs to scrape")

    successful = 0
    for i, url in enumerate(recipe_urls, 1):
        print(f"\n[{i}/{len(recipe_urls)}] Scraping: {url}")
        recipe_data = scrape_allrecipes(url)
        if recipe_data:
            save_recipe_data(recipe_data)
            successful += 1
            print("  ✓ Success")
        else:
            print("  ✗ Failed")

    print("\n" + "=" * LOG_SEPARATOR_LENGTH)
    print(f"Summary: Successfully scraped {successful}/{len(recipe_urls)} recipes")


if __name__ == "__main__":
    main()
