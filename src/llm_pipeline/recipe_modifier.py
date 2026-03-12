"""
Step 2: Recipe Modification

This module applies structured modifications to recipes using search-and-replace operations.
It takes ModificationObject instances and applies their edits to recipe ingredients and instructions.
"""

import copy
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from loguru import logger

from .constants import (
    DEFAULT_SIMILARITY_THRESHOLD,
    VALIDATION_SIMILARITY_THRESHOLD,
    TARGET_INGREDIENTS,
    TARGET_INSTRUCTIONS,
    CHANGE_TYPE_INGREDIENT,
    CHANGE_TYPE_INSTRUCTION,
    OPERATION_REPLACE,
    OPERATION_ADD_AFTER,
    OPERATION_REMOVE,
)
from .models import (
    ModificationObject,
    ModificationEdit,
    Recipe,
    ChangeRecord
)


class RecipeModifier:
    """Applies structured modifications to recipes using search-and-replace operations."""

    def __init__(self, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        """
        Initialize the RecipeModifier.

        Args:
            similarity_threshold: Minimum similarity score for fuzzy matching (0-1)
        """
        self.similarity_threshold = similarity_threshold
        logger.info(f"Initialized RecipeModifier with similarity threshold: {similarity_threshold}")

    def find_best_match(self, target: str, candidates: List[str]) -> Tuple[Optional[str], Optional[int], float]:
        """
        Find the best matching string in a list of candidates.

        Args:
            target: String to find
            candidates: List of strings to search in

        Returns:
            Tuple of (best_match, index, similarity_score)
        """
        if not candidates:
            return None, None, 0.0

        best_match = None
        best_index = None
        best_score = 0.0

        for i, candidate in enumerate(candidates):
            similarity = SequenceMatcher(None, target.lower(), candidate.lower()).ratio()
            if similarity > best_score:
                best_score = similarity
                best_match = candidate
                best_index = i

        if best_score >= self.similarity_threshold:
            return best_match, best_index, best_score
        else:
            return None, None, best_score

    def apply_edit(
        self,
        edit: ModificationEdit,
        recipe_content: List[str]
    ) -> Tuple[List[str], List[ChangeRecord]]:
        """
        Apply a single edit to a recipe content list.

        Args:
            edit: The edit operation to apply
            recipe_content: List of ingredients or instructions

        Returns:
            Tuple of (modified_content, change_records)
        """
        modified_content = copy.deepcopy(recipe_content)
        change_records = []

        logger.debug(f"Applying {edit.operation} edit: find='{edit.find}'")

        if edit.operation == OPERATION_REPLACE:
            # Find and replace text
            match, index, score = self.find_best_match(edit.find, modified_content)

            if match and index is not None:
                original_text = modified_content[index]
                new_text = original_text.replace(edit.find, edit.replace or "")
                modified_content[index] = new_text

                change_records.append(ChangeRecord(
                    type=CHANGE_TYPE_INGREDIENT if edit.target == TARGET_INGREDIENTS else CHANGE_TYPE_INSTRUCTION,
                    from_text=original_text,
                    to_text=new_text,
                    operation=OPERATION_REPLACE
                ))

                logger.info(f"Replaced '{edit.find}' with '{edit.replace}' (similarity: {score:.2f})")
            else:
                logger.warning(f"Could not find '{edit.find}' in {edit.target} (best similarity: {score:.2f})")

        elif edit.operation == OPERATION_ADD_AFTER:
            # Add new content after finding target
            match, index, score = self.find_best_match(edit.find, modified_content)

            if match and index is not None and edit.add:
                modified_content.insert(index + 1, edit.add)

                change_records.append(ChangeRecord(
                    type=CHANGE_TYPE_INGREDIENT if edit.target == TARGET_INGREDIENTS else CHANGE_TYPE_INSTRUCTION,
                    from_text="",
                    to_text=edit.add,
                    operation="add"
                ))

                logger.info(f"Added '{edit.add}' after '{edit.find}' (similarity: {score:.2f})")
            else:
                logger.warning(f"Could not find target '{edit.find}' for addition")

        elif edit.operation == OPERATION_REMOVE:
            # Remove matching content
            match, index, score = self.find_best_match(edit.find, modified_content)

            if match and index is not None:
                removed_text = modified_content.pop(index)

                change_records.append(ChangeRecord(
                    type=CHANGE_TYPE_INGREDIENT if edit.target == TARGET_INGREDIENTS else CHANGE_TYPE_INSTRUCTION,
                    from_text=removed_text,
                    to_text="",
                    operation=OPERATION_REMOVE
                ))

                logger.info(f"Removed '{edit.find}' (similarity: {score:.2f})")
            else:
                logger.warning(f"Could not find '{edit.find}' to remove")

        return modified_content, change_records

    def apply_modification(
        self,
        recipe: Recipe,
        modification: ModificationObject
    ) -> Tuple[Recipe, List[ChangeRecord]]:
        """
        Apply a complete modification to a recipe.

        Args:
            recipe: Original recipe to modify
            modification: Structured modification to apply

        Returns:
            Tuple of (modified_recipe, all_change_records)
        """
        logger.info(f"Applying {modification.modification_type} with {len(modification.edits)} edits")

        # Deep copy the recipe
        modified_recipe = Recipe(
            recipe_id=f"{recipe.recipe_id}_modified",
            title=recipe.title,
            ingredients=copy.deepcopy(recipe.ingredients),
            instructions=copy.deepcopy(recipe.instructions),
            description=recipe.description,
            servings=recipe.servings,
            rating=recipe.rating
        )

        all_change_records = []

        # Apply each edit
        for edit in modification.edits:
            if edit.target == TARGET_INGREDIENTS:
                modified_recipe.ingredients, change_records = self.apply_edit(
                    edit, modified_recipe.ingredients
                )
            elif edit.target == TARGET_INSTRUCTIONS:
                modified_recipe.instructions, change_records = self.apply_edit(
                    edit, modified_recipe.instructions
                )
            else:
                logger.warning(f"Unknown edit target: {edit.target}")
                continue

            all_change_records.extend(change_records)

        logger.info(f"Applied modification successfully: {len(all_change_records)} changes made")
        return modified_recipe, all_change_records

    def apply_modifications_batch(
        self,
        recipe: Recipe,
        modifications: List[ModificationObject]
    ) -> Tuple[Recipe, List[List[ChangeRecord]]]:
        """
        Apply multiple modifications to a recipe sequentially.

        Args:
            recipe: Original recipe to modify
            modifications: List of modifications to apply

        Returns:
            Tuple of (final_modified_recipe, list_of_change_records_per_modification)
        """
        current_recipe = recipe
        all_change_records = []

        logger.info(f"Applying {len(modifications)} modifications sequentially")

        for i, modification in enumerate(modifications):
            logger.info(f"Applying modification {i + 1}/{len(modifications)}: {modification.modification_type}")

            current_recipe, change_records = self.apply_modification(current_recipe, modification)
            all_change_records.append(change_records)

        logger.info(f"Applied all modifications. Final recipe has {len(current_recipe.ingredients)} ingredients and {len(current_recipe.instructions)} instructions")
        return current_recipe, all_change_records

    def validate_modification_safety(
        self,
        modification: ModificationObject,
        recipe: Recipe
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a modification won't break the recipe.

        Args:
            modification: Modification to validate
            recipe: Recipe being modified

        Returns:
            Tuple of (is_safe, list_of_warnings)
        """
        warnings = []
        is_safe = True

        for edit in modification.edits:
            # Check if target content exists
            target_content = recipe.ingredients if edit.target == TARGET_INGREDIENTS else recipe.instructions
            match, _, score = self.find_best_match(edit.find, target_content)

            if not match:
                warnings.append(f"Cannot find '{edit.find}' in {edit.target}")
                is_safe = False
            elif score < VALIDATION_SIMILARITY_THRESHOLD:
                warnings.append(f"Low similarity match for '{edit.find}' (score: {score:.2f})")

            # Check for required fields
            if edit.operation == OPERATION_REPLACE and not edit.replace:
                warnings.append(f"Replace operation missing replacement text for '{edit.find}'")
                is_safe = False
            elif edit.operation == OPERATION_ADD_AFTER and not edit.add:
                warnings.append(f"Add operation missing text to add after '{edit.find}'")
                is_safe = False

        return is_safe, warnings