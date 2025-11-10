# Refresh Index

## Motivation

Use single book to manage transactions is hard. The usually split books by year or months. However, it need manual work to list related files to index file.

## Usage

```
bean-tw refresh
```

- Recursively scan all Beancount files under the specified directory (default to `./books/`).
- Update the index file recursively (e.g. `./books/index.bean`, `./books/2024/index.bean`).

## Index File

The index file usually named `index.bean` or `index.beancount` under each directory. It design to include all Beancount files under the same directory.

- `index.bean`
- `books.bean`
- `index.beancount`
- `books.beancount`

## Scenarios

```gherkin
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
```

```gherkin
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
```

```gherkin
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
```

```gherkin
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
```
