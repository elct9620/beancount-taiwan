"""Service for managing Beancount index files.

This module provides file system operations for reading and writing
Beancount index files.
"""

import re
from pathlib import Path
from typing import Protocol, Set


class IndexServiceProtocol(Protocol):
    """Protocol defining the interface for index file services."""

    def find_beancount_files(
        self, dir_path: Path, exclude_index: bool = True
    ) -> list[Path]:
        """Find all Beancount files in a directory (non-recursive).

        Args:
            dir_path: Path to the directory to search
            exclude_index: Whether to exclude index files from results

        Returns:
            List of Beancount file paths
        """
        ...

    def find_subdirectory_indexes(self, dir_path: Path) -> list[Path]:
        """Find all index files in immediate subdirectories.

        Args:
            dir_path: Path to the directory to search

        Returns:
            List of index file paths in subdirectories
        """
        ...

    def get_or_create_index_file(self, dir_path: Path) -> Path | None:
        """Find existing index file or determine which one to create.

        Args:
            dir_path: Path to the directory

        Returns:
            Path to the index file, or None if no existing index found
        """
        ...

    def read_existing_includes(self, index_file: Path) -> Set[str]:
        """Read existing include statements from an index file.

        Args:
            index_file: Path to the index file

        Returns:
            Set of include statements (normalized)
        """
        ...

    def write_index_file(self, index_file: Path, includes: list[str]) -> None:
        """Write include statements to an index file.

        Args:
            index_file: Path to the index file
            includes: List of include statements to write
        """
        ...


class IndexService:
    """Service for managing Beancount index files.

    This service handles file system operations for reading and writing
    Beancount index files.
    """

    # Valid index file names (in order of preference for creation)
    INDEX_FILENAMES = ["index.bean", "books.bean", "index.beancount", "books.beancount"]

    # Valid Beancount file extensions
    BEANCOUNT_EXTENSIONS = {".bean", ".beancount"}

    def find_beancount_files(
        self, dir_path: Path, exclude_index: bool = True
    ) -> list[Path]:
        """Find all Beancount files in a directory (non-recursive).

        Args:
            dir_path: Path to the directory to search
            exclude_index: Whether to exclude index files from results

        Returns:
            List of Beancount file paths
        """
        beancount_files = []

        for item in dir_path.iterdir():
            if not item.is_file():
                continue

            # Check if it's a beancount file
            if item.suffix not in self.BEANCOUNT_EXTENSIONS:
                continue

            # Exclude index files if requested
            if exclude_index and item.name in self.INDEX_FILENAMES:
                continue

            beancount_files.append(item)

        return beancount_files

    def find_subdirectory_indexes(self, dir_path: Path) -> list[Path]:
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

    def get_or_create_index_file(self, dir_path: Path) -> Path | None:
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

    def read_existing_includes(self, index_file: Path) -> Set[str]:
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

    def write_index_file(self, index_file: Path, includes: list[str]) -> None:
        """Write include statements to an index file.

        Args:
            index_file: Path to the index file
            includes: List of include statements to write
        """
        content = "\n".join(includes) + "\n"
        index_file.write_text(content, encoding="utf-8")
