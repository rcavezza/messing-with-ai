#!/usr/bin/env python3
"""
LLM Analysis Pipeline Test Script

This script provides a flexible interface for testing the recipe enhancement pipeline.

Usage:
    # Test a specific recipe
    python test_pipeline.py recipe_10813_best-chocolate-chip-cookies.json
    
    # Test all recipes
    python test_pipeline.py all
    
    # Test with default recipe (chocolate chip cookies)
    python test_pipeline.py
"""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

from llm_pipeline.constants import LOG_SEPARATOR_LENGTH
from llm_pipeline.pipeline import LLMAnalysisPipeline
from llm_pipeline.paths import (
    get_recipe_file_path,
    get_data_directory,
    get_enhanced_directory,
    find_all_recipe_files,
)

# Load environment variables
load_dotenv()

# Default recipe for quick testing
DEFAULT_RECIPE = "recipe_10813_best-chocolate-chip-cookies.json"


def ensure_api_key() -> bool:
    """
    Check if OpenAI API key is set.
    
    Returns:
        True if API key is available, False otherwise
    """
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        logger.info("Please set your OpenAI API key in .env file")
        return False
    return True


def initialize_pipeline(output_dir: Optional[Path] = None) -> Optional[LLMAnalysisPipeline]:
    """
    Initialize the LLM Analysis Pipeline.
    
    Args:
        output_dir: Optional custom output directory (defaults to data/enhanced)
    
    Returns:
        Initialized pipeline or None if initialization fails
    """
    try:
        if output_dir is None:
            output_dir = get_enhanced_directory()
        
        pipeline = LLMAnalysisPipeline(output_dir=str(output_dir))
        logger.info("Pipeline initialized successfully")
        return pipeline
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        return None


def process_single_recipe(recipe_file: str, process_all_reviews: bool = False) -> bool:
    """
    Process a single recipe through the pipeline.

    Args:
        recipe_file: Path or filename of recipe to process
        process_all_reviews: If True, process all reviews with modifications;
                            if False, process one random review (default)

    Returns:
        True if successful, False otherwise
    """
    if not ensure_api_key():
        return False

    pipeline = initialize_pipeline()
    if not pipeline:
        return False

    try:
        # Resolve recipe file path
        recipe_path = get_recipe_file_path(recipe_file)
        mode_text = "all reviews" if process_all_reviews else "one random review"
        logger.info(f"Processing recipe: {recipe_path.name} ({mode_text})")

        # Process the recipe
        enhanced_recipe = pipeline.process_single_recipe(
            recipe_file=str(recipe_path),
            save_output=True,
            process_all_reviews=process_all_reviews,
        )
        
        if enhanced_recipe:
            logger.success("✓ Recipe processed successfully!")
            logger.info(f"Enhanced recipe: {enhanced_recipe.title}")
            logger.info(f"Modifications applied: {len(enhanced_recipe.modifications_applied)}")
            logger.info(f"Total changes: {enhanced_recipe.enhancement_summary.total_changes}")
            logger.info(f"Expected impact: {enhanced_recipe.enhancement_summary.expected_impact}")
            logger.info(f"Output saved to: {get_enhanced_directory()}")
            return True
        else:
            logger.error("✗ Failed to generate enhanced recipe")
            return False
            
    except FileNotFoundError as e:
        logger.error(str(e))
        return False
    except Exception as e:
        logger.error(f"Recipe processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def process_all_recipes() -> bool:
    """
    Process all recipes in the data directory.
    
    Returns:
        True if at least one recipe was processed successfully, False otherwise
    """
    if not ensure_api_key():
        return False
    
    pipeline = initialize_pipeline()
    if not pipeline:
        return False
    
    try:
        data_dir = get_data_directory()
        logger.info(f"Processing all recipes from: {data_dir}")
        
        # Process all recipes
        enhanced_recipes = pipeline.process_recipe_directory(data_dir=str(data_dir))
        
        # Generate summary report
        report_path = pipeline.save_summary_report(enhanced_recipes)
        
        logger.info(f"\n{'=' * LOG_SEPARATOR_LENGTH}")
        logger.success("✓ All recipes processing complete!")
        logger.info(f"Enhanced recipes: {len(enhanced_recipes)}")
        logger.info(f"Summary report: {report_path}")
        logger.info(f"Enhanced recipes saved to: {get_enhanced_directory()}")
        
        return len(enhanced_recipes) > 0
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_available_recipes() -> None:
    """List all available recipe files."""
    recipes = find_all_recipe_files()
    
    if not recipes:
        logger.warning(f"No recipe files found in {get_data_directory()}")
        return
    
    logger.info(f"Available recipes ({len(recipes)}):")
    for recipe in recipes:
        logger.info(f"  - {recipe.name}")


def print_usage() -> None:
    """Print usage information."""
    logger.info("Usage:")
    logger.info("  python test_pipeline.py [recipe_file|all|list] [--all-reviews]")
    logger.info("")
    logger.info("Examples:")
    logger.info("  python test_pipeline.py                                    # Test default recipe (one review)")
    logger.info("  python test_pipeline.py recipe_25346_coconut-rice.json     # Test specific recipe (one review)")
    logger.info("  python test_pipeline.py recipe_25346_coconut-rice.json --all-reviews  # Process ALL reviews")
    logger.info("  python test_pipeline.py all                                # Process all recipes (one review each)")
    logger.info("  python test_pipeline.py list                               # List available recipes")
    logger.info("")
    logger.info("Flags:")
    logger.info("  --all-reviews    Process ALL reviews with modifications (default: one random review)")
    logger.info("")
    logger.info(f"Default recipe: {DEFAULT_RECIPE}")
    logger.info(f"Data directory: {get_data_directory()}")
    logger.info(f"Output directory: {get_enhanced_directory()}")


def main() -> None:
    """Main entry point for the test script."""

    # Parse command line arguments
    args = sys.argv[1:]
    
    # Check for --all-reviews flag
    process_all_reviews = "--all-reviews" in args
    if process_all_reviews:
        args.remove("--all-reviews")

    if len(args) == 0:
        # No arguments - use default recipe
        mode_text = "all reviews" if process_all_reviews else "one review"
        logger.info(f"No recipe specified, using default recipe ({mode_text})")
        logger.info("=" * LOG_SEPARATOR_LENGTH)
        success = process_single_recipe(DEFAULT_RECIPE, process_all_reviews=process_all_reviews)
        logger.info("=" * LOG_SEPARATOR_LENGTH)

        if success:
            logger.success("Default recipe test passed! ✓")
        else:
            logger.error("Default recipe test failed! ✗")
            sys.exit(1)
        return

    command = args[0].lower()

    if command == "all":
        mode_text = "all reviews per recipe" if process_all_reviews else "one review per recipe"
        logger.info(f"Starting LLM Analysis Pipeline - All Recipes ({mode_text})")
        logger.info("=" * LOG_SEPARATOR_LENGTH)
        
        # Note: process_all_recipes doesn't support --all-reviews yet
        # For now, we'll process each recipe with one review
        if process_all_reviews:
            logger.warning("--all-reviews flag not yet supported for 'all' mode")
            logger.info("Processing each recipe with one random review")
        
        success = process_all_recipes()
        logger.info("=" * LOG_SEPARATOR_LENGTH)

        if success:
            logger.success("All recipes processing complete! ✓")
        else:
            logger.error("All recipes processing failed! ✗")
            sys.exit(1)

    elif command == "list":
        list_available_recipes()

    elif command in ["help", "-h", "--help"]:
        print_usage()

    else:
        # Treat as recipe filename
        mode_text = "all reviews" if process_all_reviews else "one review"
        logger.info(f"Starting LLM Analysis Pipeline - Single Recipe ({mode_text})")
        logger.info("=" * LOG_SEPARATOR_LENGTH)
        success = process_single_recipe(command, process_all_reviews=process_all_reviews)
        logger.info("=" * LOG_SEPARATOR_LENGTH)

        if success:
            logger.success("Recipe processing complete! ✓")
        else:
            logger.error("Recipe processing failed! ✗")
            sys.exit(1)


if __name__ == "__main__":
    main()
