"""Tests for refresh use case functionality."""

import tempfile
from pathlib import Path

import pytest

from beantw.usecases.refresh import RefreshUseCase


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_refresh_creates_index_files_in_nested_directories(temp_dir):
    """Test that refresh creates index files for nested directory structure.

    Scenario: Refresh Beancount index files
      Given the following Beancount files exist:
        | Path                | Content                                            |
        | books/2023/jan.bean | 2023-01-01 * "New Year" Assets:Cash 1000           |
        | books/2023/feb.bean | 2023-02-14 * "Valentine's Day" Expenses:Dining 200 |
        | books/2024/mar.bean | 2024-03-10 * "Birthday" Expenses:Gifts 300         |
      When I run `bean-tw refresh`
      Then the following index files should be created or updated:
        | Path                  | Content                                                |
        | books/2023/index.bean | include "jan.bean" \n include "feb.bean"               |
        | books/2024/index.bean | include "mar.bean"                                     |
        | books/index.bean      | include "2023/index.bean" \n include "2024/index.bean" |
    """
    # Create directory structure
    books_dir = temp_dir / "books"
    (books_dir / "2023").mkdir(parents=True)
    (books_dir / "2024").mkdir(parents=True)

    # Create beancount files
    (books_dir / "2023" / "jan.bean").write_text(
        '2023-01-01 * "New Year"\n  Assets:Cash 1000 TWD\n'
    )
    (books_dir / "2023" / "feb.bean").write_text(
        '2023-02-14 * "Valentine\'s Day"\n  Expenses:Dining 200 TWD\n'
    )
    (books_dir / "2024" / "mar.bean").write_text(
        '2024-03-10 * "Birthday"\n  Expenses:Gifts 300 TWD\n'
    )

    # Execute refresh
    use_case = RefreshUseCase()
    use_case.execute(str(books_dir))

    # Verify index files were created
    assert (books_dir / "2023" / "index.bean").exists()
    assert (books_dir / "2024" / "index.bean").exists()
    assert (books_dir / "index.bean").exists()

    # Verify content of 2023 index
    content_2023 = (books_dir / "2023" / "index.bean").read_text()
    assert 'include "feb.bean"' in content_2023
    assert 'include "jan.bean"' in content_2023

    # Verify content of 2024 index
    content_2024 = (books_dir / "2024" / "index.bean").read_text()
    assert 'include "mar.bean"' in content_2024

    # Verify content of root index
    content_root = (books_dir / "index.bean").read_text()
    assert 'include "2023/index.bean"' in content_root
    assert 'include "2024/index.bean"' in content_root


def test_refresh_with_custom_directory(temp_dir):
    """Test refresh with custom directory path.

    Scenario: Refresh Beancount index files with custom directory
      Given the following Beancount files exist:
        | Path                   | Content                                               |
        | my_books/2022/apr.bean | 2022-04-01 * "April Fools" Expenses:Entertainment 150 |
        | my_books/2022/may.bean | 2022-05-01 * "Labor Day" Assets:Cash 500              |
      When I run `bean-tw refresh --dir my_books/`
      Then the following index files should be created or updated:
        | Path                     | Content                                  |
        | my_books/2022/index.bean | include "apr.bean" \n include "may.bean" |
        | my_books/index.bean      | include "2022/index.bean"                |
    """
    # Create directory structure
    books_dir = temp_dir / "my_books"
    (books_dir / "2022").mkdir(parents=True)

    # Create beancount files
    (books_dir / "2022" / "apr.bean").write_text(
        '2022-04-01 * "April Fools"\n  Expenses:Entertainment 150 TWD\n'
    )
    (books_dir / "2022" / "may.bean").write_text(
        '2022-05-01 * "Labor Day"\n  Assets:Cash 500 TWD\n'
    )

    # Execute refresh
    use_case = RefreshUseCase()
    use_case.execute(str(books_dir))

    # Verify index files
    assert (books_dir / "2022" / "index.bean").exists()
    assert (books_dir / "index.bean").exists()

    # Verify content
    content_2022 = (books_dir / "2022" / "index.bean").read_text()
    assert 'include "apr.bean"' in content_2022
    assert 'include "may.bean"' in content_2022

    content_root = (books_dir / "index.bean").read_text()
    assert 'include "2022/index.bean"' in content_root


def test_refresh_preserves_existing_includes(temp_dir):
    """Test that refresh preserves existing includes when updating index files.

    Scenario: Refresh Beancount index files with existing index files
      Given the following Beancount files exist:
        | Path                  | Content                                                  |
        | books/2023/jun.bean   | 2023-06-01 * "Children's Day" Expenses:Entertainment 250 |
        | books/2023/jul.bean   | 2023-07-04 * "Independence Day" Assets:Cash 400          |
        | books/2023/index.bean | include "jan.bean"                                       |
      When I run `bean-tw refresh`
      Then the following index files should be created or updated:
        | Path                  | Content                                                        |
        | books/2023/index.bean | include "jan.bean" \n include "jun.bean" \n include "jul.bean" |
    """
    # Create directory structure
    books_dir = temp_dir / "books"
    (books_dir / "2023").mkdir(parents=True)

    # Create existing index file
    (books_dir / "2023" / "index.bean").write_text('include "jan.bean"\n')

    # Create new beancount files
    (books_dir / "2023" / "jun.bean").write_text(
        '2023-06-01 * "Children\'s Day"\n  Expenses:Entertainment 250 TWD\n'
    )
    (books_dir / "2023" / "jul.bean").write_text(
        '2023-07-04 * "Independence Day"\n  Assets:Cash 400 TWD\n'
    )

    # Execute refresh
    use_case = RefreshUseCase()
    use_case.execute(str(books_dir))

    # Verify index file updated
    content = (books_dir / "2023" / "index.bean").read_text()
    assert 'include "jan.bean"' in content
    assert 'include "jun.bean"' in content
    assert 'include "jul.bean"' in content


def test_refresh_supports_books_bean_as_index(temp_dir):
    """Test that refresh works with books.bean as index file.

    Scenario: Support use books.bean as index file
      Given the following Beancount files exist:
        | Path                | Content                                              |
        | books/2025/aug.bean | 2025-08-15 * "Summer Vacation" Expenses:Travel 800   |
        | books/2025/sep.bean | 2025-09-01 * "Back to School" Expenses:Education 600 |
        | books/books.bean    | include "2024/index.bean"                            |
      When I run `bean-tw refresh`
      Then the following index files should be created or updated:
        | Path                  | Content                                                |
        | books/2025/index.bean | include "aug.bean" \n include "sep.bean"               |
        | books/books.bean      | include "2024/index.bean" \n include "2025/index.bean" |
    """
    # Create directory structure
    books_dir = temp_dir / "books"
    (books_dir / "2025").mkdir(parents=True)

    # Create existing books.bean file
    (books_dir / "books.bean").write_text('include "2024/index.bean"\n')

    # Create beancount files
    (books_dir / "2025" / "aug.bean").write_text(
        '2025-08-15 * "Summer Vacation"\n  Expenses:Travel 800 TWD\n'
    )
    (books_dir / "2025" / "sep.bean").write_text(
        '2025-09-01 * "Back to School"\n  Expenses:Education 600 TWD\n'
    )

    # Execute refresh
    use_case = RefreshUseCase()
    use_case.execute(str(books_dir))

    # Verify index files
    assert (books_dir / "2025" / "index.bean").exists()

    # Verify content of 2025 index
    content_2025 = (books_dir / "2025" / "index.bean").read_text()
    assert 'include "aug.bean"' in content_2025
    assert 'include "sep.bean"' in content_2025

    # Verify books.bean was updated
    content_root = (books_dir / "books.bean").read_text()
    assert 'include "2024/index.bean"' in content_root
    assert 'include "2025/index.bean"' in content_root


def test_refresh_handles_beancount_extension(temp_dir):
    """Test that refresh handles .beancount extension files."""
    # Create directory structure
    books_dir = temp_dir / "books"
    books_dir.mkdir()

    # Create .beancount files
    (books_dir / "jan.beancount").write_text(
        '2023-01-01 * "Test"\n  Assets:Cash 100 TWD\n'
    )
    (books_dir / "feb.beancount").write_text(
        '2023-02-01 * "Test"\n  Assets:Cash 200 TWD\n'
    )

    # Execute refresh
    use_case = RefreshUseCase()
    use_case.execute(str(books_dir))

    # Should create index.bean (or similar) with .beancount files included
    # Check for any of the valid index file names
    index_files = list(books_dir.glob("index.*")) + list(books_dir.glob("books.*"))
    assert len(index_files) > 0

    content = index_files[0].read_text()
    assert 'include "feb.beancount"' in content or 'include "jan.beancount"' in content


def test_refresh_skips_empty_directories(temp_dir):
    """Test that refresh doesn't create index files in empty directories."""
    # Create directory structure with empty directory
    books_dir = temp_dir / "books"
    (books_dir / "2023").mkdir(parents=True)
    (books_dir / "2024").mkdir(parents=True)

    # Only create file in 2023
    (books_dir / "2023" / "jan.bean").write_text(
        '2023-01-01 * "Test"\n  Assets:Cash 100 TWD\n'
    )

    # Execute refresh
    use_case = RefreshUseCase()
    use_case.execute(str(books_dir))

    # Should create index in 2023 but not in empty 2024
    assert (books_dir / "2023" / "index.bean").exists()
    # 2024 should not have an index file since it's empty
    assert not (books_dir / "2024" / "index.bean").exists()
