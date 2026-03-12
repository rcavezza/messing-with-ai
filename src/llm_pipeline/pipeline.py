"""
LLM Analysis Pipeline - Main Orchestrator

This module coordinates the complete 3-step pipeline:
1. Extract modifications from reviews
2. Apply modifications to recipes
3. Generate enhanced recipes with attribution

Processes recipe data from scraped JSON files and outputs enhanced recipes.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from loguru import logger

from .constants import (
    LOG_SEPARATOR_LENGTH,
    RECIPE_TITLE_MAX_LENGTH,
    JSON_INDENT_LEVEL,
)
from .enhanced_recipe_generator import EnhancedRecipeGenerator
from .models import EnhancedRecipe, Recipe, Review
from .recipe_modifier import RecipeModifier
from .tweak_extractor import TweakExtractor


class LLMAnalysisPipeline:
    """Complete pipeline for analyzing recipes and generating enhanced versions."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        output_dir: Optional[str] = None,
        pipeline_version: str = "1.0.0",
    ):
        """
        Initialize the complete LLM Analysis Pipeline.

        Args:
            openai_api_key: OpenAI API key (loads from env if not provided)
            output_dir: Directory to save enhanced recipes (defaults to project_root/data/enhanced)
            pipeline_version: Version identifier for tracking
        """
        # Load environment variables
        load_dotenv()

        # Use default output directory if not specified
        if output_dir is None:
            from .paths import get_enhanced_directory
            output_dir = str(get_enhanced_directory())

        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize pipeline components
        self.tweak_extractor = TweakExtractor(api_key=openai_api_key)
        self.recipe_modifier = RecipeModifier()
        self.enhanced_generator = EnhancedRecipeGenerator(
            pipeline_version=pipeline_version
        )

        logger.info(f"Initialized LLM Analysis Pipeline v{pipeline_version}")
        logger.info(f"Output directory: {self.output_dir}")

    def load_recipe_data(self, file_path: str) -> Dict[str, Any]:
        """
        Load recipe data from JSON file.

        Args:
            file_path: Path to recipe JSON file

        Returns:
            Recipe data dictionary
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def parse_recipe_data(self, recipe_data: Dict[str, Any]) -> Recipe:
        """
        Parse raw recipe data into Recipe object.

        Args:
            recipe_data: Raw recipe data from JSON

        Returns:
            Recipe object
        """
        return Recipe(
            recipe_id=recipe_data.get("recipe_id", "unknown"),
            title=recipe_data.get("title", "Unknown Recipe"),
            ingredients=recipe_data.get("ingredients", []),
            instructions=recipe_data.get("instructions", []),
            description=recipe_data.get("description"),
            servings=recipe_data.get("servings"),
            rating=recipe_data.get("rating"),
        )

    def parse_reviews_data(self, recipe_data: Dict[str, Any]) -> List[Review]:
        """
        Parse raw review data into Review objects.

        Args:
            recipe_data: Raw recipe data containing reviews

        Returns:
            List of Review objects
        """
        reviews = []
        raw_reviews = recipe_data.get("reviews", [])

        for review_data in raw_reviews:
            if review_data.get("text"):
                review = Review(
                    text=review_data["text"],
                    rating=review_data.get("rating"),
                    username=review_data.get("username"),
                    has_modification=review_data.get("has_modification", False),
                )
                reviews.append(review)

        return reviews

    def process_single_recipe(
        self,
        recipe_file: str,
        save_output: bool = True,
        process_all_reviews: bool = False,
    ) -> Optional[EnhancedRecipe]:
        """
        Process a single recipe through the complete pipeline.

        Args:
            recipe_file: Path to recipe JSON file
            save_output: Whether to save the enhanced recipe
            process_all_reviews: If True, process all reviews with modifications;
                                 if False, process one random review (default)

        Returns:
            EnhancedRecipe if successful, None otherwise
        """
        try:
            logger.info(f"Processing recipe file: {recipe_file}")

            # Step 0: Load and parse data
            recipe_data = self.load_recipe_data(recipe_file)
            recipe = self.parse_recipe_data(recipe_data)
            reviews = self.parse_reviews_data(recipe_data)

            logger.info(f"Loaded recipe: {recipe.title}")
            modification_reviews_count = len([r for r in reviews if r.has_modification])
            logger.info(
                f"Found {len(reviews)} reviews, {modification_reviews_count} with modifications"
            )

            if not any(r.has_modification for r in reviews):
                logger.warning("No reviews with modifications found")
                return None

            if process_all_reviews:
                return self._process_all_reviews(recipe, reviews)
            else:
                return self._process_single_review(recipe, reviews, save_output)

        except Exception as e:
            logger.error(f"Failed to process recipe {recipe_file}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _process_single_review(
        self, recipe: Recipe, reviews: List[Review], save_output: bool
    ) -> Optional[EnhancedRecipe]:
        """
        Process recipe with a single randomly selected review.

        Args:
            recipe: Parsed recipe object
            reviews: List of reviews
            save_output: Whether to save the enhanced recipe

        Returns:
            EnhancedRecipe if successful, None otherwise
        """
        # Step 1: Extract modification from one random review
        logger.info("Step 1: Extracting modification from a single review...")
        modification, source_review = (
            self.tweak_extractor.extract_single_modification(reviews, recipe)
        )

        if not modification or not source_review:
            logger.warning("No modification could be extracted")
            return None

        logger.info(
            f"Successfully extracted {modification.modification_type} modification"
        )

        # Step 2: Apply modification to recipe
        logger.info("Step 2: Applying modification to recipe...")
        modified_recipe, change_records = self.recipe_modifier.apply_modification(
            recipe, modification
        )

        logger.info(
            f"Applied modification: {len(change_records)} total changes made"
        )

        # Step 3: Generate enhanced recipe with attribution
        logger.info("Step 3: Generating enhanced recipe with attribution...")

        enhanced_recipe = self.enhanced_generator.generate_enhanced_recipe(
            recipe, modified_recipe, modification, source_review, change_records
        )

        logger.info(f"Generated enhanced recipe: {enhanced_recipe.title}")

        # Save output
        if save_output:
            output_filename = f"enhanced_{recipe.recipe_id}_{recipe.title.lower().replace(' ', '-')[:RECIPE_TITLE_MAX_LENGTH]}.json"
            output_path = self.output_dir / output_filename
            self.enhanced_generator.save_enhanced_recipe(
                enhanced_recipe, str(output_path)
            )

        return enhanced_recipe

    def _process_all_reviews(
        self, recipe: Recipe, reviews: List[Review]
    ) -> Optional[EnhancedRecipe]:
        """
        Process recipe with ALL reviews that have modifications.

        Args:
            recipe: Parsed recipe object
            reviews: List of reviews

        Returns:
            EnhancedRecipe with all modifications applied, None if no modifications extracted
        """
        # Step 1: Extract modifications from ALL reviews
        logger.info("Step 1: Extracting modifications from ALL reviews...")
        extracted_modifications = self.tweak_extractor.extract_all_modifications(
            reviews, recipe
        )

        if not extracted_modifications:
            logger.warning("No modifications could be extracted from any review")
            return None

        logger.info(
            f"Successfully extracted {len(extracted_modifications)} modifications"
        )

        # Step 2: Apply all modifications sequentially
        logger.info("Step 2: Applying all modifications sequentially...")

        modifications = [mod for mod, _ in extracted_modifications]
        modified_recipe, all_change_records = self.recipe_modifier.apply_modifications_batch(
            recipe, modifications
        )

        total_changes = sum(len(records) for records in all_change_records)
        logger.info(f"Applied all modifications: {total_changes} total changes made")

        # Step 3: Generate enhanced recipe with all attributions
        logger.info("Step 3: Generating enhanced recipe with all attributions...")

        enhanced_recipe = self.enhanced_generator.generate_enhanced_recipe_with_all_modifications(
            recipe, modified_recipe, extracted_modifications, all_change_records
        )

        logger.info(f"Generated enhanced recipe: {enhanced_recipe.title}")

        # Save output
        output_filename = f"enhanced_{recipe.recipe_id}_{recipe.title.lower().replace(' ', '-')[:RECIPE_TITLE_MAX_LENGTH]}.json"
        output_path = self.output_dir / output_filename
        self.enhanced_generator.save_enhanced_recipe(enhanced_recipe, str(output_path))

        return enhanced_recipe

    def process_recipe_directory(self, data_dir: Optional[str] = None) -> List[EnhancedRecipe]:
        """
        Process all recipe files in a directory.

        Args:
            data_dir: Directory containing recipe JSON files (defaults to project_root/data)

        Returns:
            List of successfully processed EnhancedRecipe objects
        """
        if data_dir is None:
            from .paths import get_data_directory
            data_path = get_data_directory()
        else:
            data_path = Path(data_dir).resolve()
        
        recipe_files = list(data_path.glob("recipe_*.json"))

        logger.info(f"Found {len(recipe_files)} recipe files to process")

        enhanced_recipes = []
        for recipe_file in recipe_files:
            logger.info(f"\n{'=' * LOG_SEPARATOR_LENGTH}")
            enhanced_recipe = self.process_single_recipe(str(recipe_file))

            if enhanced_recipe:
                enhanced_recipes.append(enhanced_recipe)
                logger.info(f"✓ Successfully processed: {enhanced_recipe.title}")
            else:
                logger.warning(f"✗ Failed to process: {recipe_file.name}")

        logger.info(f"\n{'=' * LOG_SEPARATOR_LENGTH}")
        logger.info(
            f"Pipeline complete: {len(enhanced_recipes)}/{len(recipe_files)} recipes successfully enhanced"
        )

        return enhanced_recipes

    def generate_summary_report(
        self, enhanced_recipes: List[EnhancedRecipe]
    ) -> Dict[str, Any]:
        """
        Generate a summary report of pipeline results.

        Args:
            enhanced_recipes: List of enhanced recipes

        Returns:
            Summary report dictionary
        """
        if not enhanced_recipes:
            return {"status": "no_recipes_processed"}

        total_modifications = sum(
            len(recipe.modifications_applied) for recipe in enhanced_recipes
        )
        total_changes = sum(
            recipe.enhancement_summary.total_changes for recipe in enhanced_recipes
        )

        change_type_counts = {}
        for recipe in enhanced_recipes:
            for change_type in recipe.enhancement_summary.change_types:
                change_type_counts[change_type] = (
                    change_type_counts.get(change_type, 0) + 1
                )

        report = {
            "pipeline_summary": {
                "recipes_processed": len(enhanced_recipes),
                "total_modifications_applied": total_modifications,
                "total_changes_made": total_changes,
                "change_type_distribution": change_type_counts,
            },
            "enhanced_recipes": [
                {
                    "recipe_id": recipe.recipe_id,
                    "title": recipe.title,
                    "modifications_count": len(recipe.modifications_applied),
                    "changes_count": recipe.enhancement_summary.total_changes,
                    "change_types": recipe.enhancement_summary.change_types,
                }
                for recipe in enhanced_recipes
            ],
        }

        return report

    def save_summary_report(
        self, enhanced_recipes: List[EnhancedRecipe], output_path: Optional[str] = None
    ) -> str:
        """
        Save pipeline summary report to JSON file.

        Args:
            enhanced_recipes: List of enhanced recipes
            output_path: Path to save report (auto-generated if None)

        Returns:
            Path to saved report
        """
        if output_path is None:
            output_path = str(self.output_dir / "pipeline_summary_report.json")

        report = self.generate_summary_report(enhanced_recipes)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=JSON_INDENT_LEVEL, ensure_ascii=False)

        logger.info(f"Saved pipeline summary report to: {output_path}")
        return output_path
