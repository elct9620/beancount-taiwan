"""Use case for refreshing Beancount index files.

This module provides functionality to recursively scan directories for Beancount files
and automatically create/update index files that include all related files.
"""

import re
from pathlib import Path
from typing import Set


class RefreshUseCase:
    """Use case for refreshing Beancount index files.

    This use case scans a directory recursively for Beancount files and automatically
    creates or updates index files in each directory. Index files contain include
    directives for all Beancount files in the same directory.
    """

    # Valid index file names (in order of preference for creation)
    INDEX_FILENAMES = ["index.bean", "books.bean", "index.beancount", "books.beancount"]

    # Valid Beancount file extensions
    BEANCOUNT_EXTENSIONS = {".bean", ".beancount"}

    def __init__(self):
        """Initialize the RefreshUseCase."""
        pass

    def execute(self, directory: str) -> None:
        """Execute the refresh operation on the specified directory.

        Args:
            directory: Path to the directory to scan for Beancount files

        Raises:
            ValueError: If the directory does not exist
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        if not dir_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # Process the directory tree bottom-up (children first, then parents)
        self._refresh_directory_recursive(dir_path)

    def _refresh_directory_recursive(self, dir_path: Path) -> None:
        """Recursively refresh index files in directory tree.

        Processes directories bottom-up to ensure child index files exist
        before parent directories reference them.

        Args:
            dir_path: Path to the directory to process
        """
        # First, recursively process all subdirectories
        for item in sorted(dir_path.iterdir()):
            if item.is_dir():
                self._refresh_directory_recursive(item)

        # Then process this directory
        self._refresh_directory(dir_path)

    def _refresh_directory(self, dir_path: Path) -> None:
        """Refresh the index file in a single directory.

        Args:
            dir_path: Path to the directory to process
        """
        # Find all beancount files in this directory (non-recursive)
        beancount_files = self._find_beancount_files(dir_path)

        # Find subdirectory index files
        subdirectory_indexes = self._find_subdirectory_indexes(dir_path)

        # Find existing index file or determine which one to create
        index_file = self._get_or_create_index_file(dir_path)

        # If no beancount files and no subdirectory indexes, skip this directory
        if not beancount_files and not subdirectory_indexes:
            return

        # Read existing includes if index file exists
        existing_includes = set()
        if index_file and index_file.exists():
            existing_includes = self._read_existing_includes(index_file)

        # Determine which index file to use/create
        if not index_file:
            # No existing index, create default one
            index_file = dir_path / self.INDEX_FILENAMES[0]

        # Build the new set of includes
        new_includes = set()

        # Add includes for regular beancount files
        for bean_file in sorted(beancount_files):
            new_includes.add(f'include "{bean_file.name}"')

        # Add includes for subdirectory indexes
        for subdir_index in sorted(subdirectory_indexes):
            relative_path = subdir_index.relative_to(dir_path)
            # Use forward slashes for include statements (Beancount standard)
            include_path = str(relative_path).replace("\\", "/")
            new_includes.add(f'include "{include_path}"')

        # Merge with existing includes (preserve any that still exist)
        all_includes = self._merge_includes(existing_includes, new_includes, dir_path)

        # Write the updated index file
        if all_includes:
            self._write_index_file(index_file, sorted(all_includes))

    def _find_beancount_files(self, dir_path: Path) -> list[Path]:
        """Find all Beancount files in a directory (non-recursive).

        Args:
            dir_path: Path to the directory to search

        Returns:
            List of Beancount file paths, excluding index files
        """
        beancount_files = []

        for item in dir_path.iterdir():
            if not item.is_file():
                continue

            # Check if it's a beancount file
            if item.suffix not in self.BEANCOUNT_EXTENSIONS:
                continue

            # Exclude index files
            if item.name in self.INDEX_FILENAMES:
                continue

            beancount_files.append(item)

        return beancount_files

    def _find_subdirectory_indexes(self, dir_path: Path) -> list[Path]:
        """Find all index files in immediate subdirectories.

        Args:
            dir_path: Path to the directory to search

        Returns:
            List of index file paths in subdirectories
        """
        subdirectory_indexes = []

        for item in dir_path.iterdir():
            if not item.is_dir():
                continue

            # Look for index files in this subdirectory
            for index_name in self.INDEX_FILENAMES:
                index_file = item / index_name
                if index_file.exists():
                    subdirectory_indexes.append(index_file)
                    break  # Only add one index file per subdirectory

        return subdirectory_indexes

    def _get_or_create_index_file(self, dir_path: Path) -> Path | None:
        """Find existing index file or determine which one to create.

        Args:
            dir_path: Path to the directory

        Returns:
            Path to the index file, or None if no existing index found
        """
        # Check for existing index files in order of preference
        for index_name in self.INDEX_FILENAMES:
            index_file = dir_path / index_name
            if index_file.exists():
                return index_file

        # No existing index file found, will create default one later
        return None

    def _read_existing_includes(self, index_file: Path) -> Set[str]:
        """Read existing include statements from an index file.

        Args:
            index_file: Path to the index file

        Returns:
            Set of include statements (normalized)
        """
        includes = set()

        try:
            content = index_file.read_text(encoding="utf-8")

            # Match include statements with various quote styles
            # Pattern matches: include "file.bean" or include 'file.bean'
            pattern = r'^\s*include\s+["\']([^"\']+)["\']\s*$'

            for line in content.splitlines():
                match = re.match(pattern, line)
                if match:
                    filename = match.group(1)
                    # Normalize to double quotes
                    includes.add(f'include "{filename}"')

        except Exception:
            # If we can't read the file, just return empty set
            pass

        return includes

    def _merge_includes(
        self, existing_includes: Set[str], new_includes: Set[str], dir_path: Path
    ) -> Set[str]:
        """Merge existing and new include statements.

        Preserves all existing includes and adds new includes for any new files.
        This allows users to maintain references to files that may not currently exist.

        Args:
            existing_includes: Set of existing include statements
            new_includes: Set of new include statements
            dir_path: Path to the directory (unused but kept for API consistency)

        Returns:
            Merged set of include statements
        """
        # Merge both sets - preserve all existing includes and add new ones
        merged = existing_includes.union(new_includes)
        return merged

    def _write_index_file(self, index_file: Path, includes: list[str]) -> None:
        """Write include statements to an index file.

        Args:
            index_file: Path to the index file
            includes: List of include statements to write
        """
        content = "\n".join(includes) + "\n"
        index_file.write_text(content, encoding="utf-8")
