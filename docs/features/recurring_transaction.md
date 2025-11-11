# Recurring Transactions

## Motivation

The user usually has some recurring transactions, such as salary, rent, utilities, subscriptions, etc. Manually adding these transactions every month is tedious and error-prone. This feature automates the process of adding recurring transactions to the Beancount ledger.

## Usage

```
bean-tw recurring
```

- According to the configured recurring transaction to add transactions to the Beancount files.
- The configuration file is usually named `recurring.yaml` or `recurring.yml` under the specified directory (default to `./config/`).

## Configuration

The configuration file defines the recurring transactions, including the frequency, amount, accounts, and description.

```yaml
# config/recurring.yaml

recurring_transactions:
  - description: "Monthly Salary"            # Transaction description
    amount: 50000                            # Transaction amount
    currency: TWD                            # Transaction currency
    source_account: Income:Salary            # Source account
    target_account: Assets:Bank:Checking     # Target account
    frequency: monthly                       # Frequency of the transaction (e.g., weekly, monthly, yearly)
    start_date: "2023-01-01"                 # Start date of the recurring transaction, used to calculate the next occurrence
    book: "books/{{year}}/{{month}}.bean"    # Target Beancount file, supports templating with year, month, and day variables

  - description: "Rent Payment"
    amount: 15000
    currency: TWD
    source_account: Expenses:Rent
    target_account: Assets:Bank:Checking
    frequency: monthly
    start_date: "2023-01-05"
    book: "books/{{year}}/{{month}}.bean"
```

The template variables available for the `book` field are:

- `{{year}}`: The year of the transaction. e.g., `2023`
- `{{month}}`: The month of the transaction, zero-padded. e.g., `01`, `02`, ..., `12`
- `{{day}}`: The day of the transaction, zero-padded. e.g., `01`, `02`, ..., `31`
- `{{month_name}}`: The full month name. e.g., `January`, `February`, ..., `December`
- `{{month_abbr}}`: The abbreviated month name. e.g., `Jan`, `Feb`, ..., `Dec`
- `{{weekday}}`: The full weekday name. e.g., `Monday`, `Tuesday`, ..., `Sunday`
- `{{weekday_abbr}}`: The abbreviated weekday name. e.g., `Mon`, `Tue`, ..., `Sun`

## Scenarios

```gherkin
Scenario: Add recurring transactions to Beancount files
  Given the following Beancount file exists:
    | Path                | Content                                  |
    | books/2023/jan.bean | 2023-01-01 * "New Year" Assets:Cash 1000 |
  And the current date is "2023-01-01"
  And the following recurring transaction configuration exists:
    """yaml
    recurring_transactions:
      - description: "Monthly Salary"
        amount: 50000
        currency: TWD
        source_account: Income:Salary
        target_account: Assets:Bank:Checking
        frequency: monthly
        start_date: "2023-01-01"
        book: "books/{{year}}/{{month}}.bean"
    """
  When I run `bean-tw recurring`
  Then the following Beancount file should be updated:
    | Path               | Content                                                                                                                                    |
    | books/2023/01.bean | 2023-01-01 * "New Year" Assets:Cash 1000\n2023-01-01 * "Monthly Salary" \nAssets:Bank:Checking 50000.00 TWD \n Income:Salary -50000.00 TWD |

Scenario: Add multiple recurring transactions to Beancount files
  Given the following Beancount file exists:
    | Path               | Content                                            |
    | books/2023/02.bean | 2023-02-14 * "Valentine's Day" Expenses:Dining 200 |
  And the current date is "2023-02-05"
  And the following recurring transaction configuration exists:
    """yaml
    recurring_transactions:
      - description: "Monthly Salary"
        amount: 50000
        currency: TWD
        source_account: Income:Salary
        target_account: Assets:Bank:Checking
        frequency: monthly
        start_date: "2023-01-01"
        book: "books/{{year}}/{{month}}.bean"
      - description: "Rent Payment"
        amount: 15000
        currency: TWD
        source_account: Expenses:Rent
        target_account: Assets:Bank:Checking
        frequency: monthly
        start_date: "2023-01-05"
        book: "books/{{year}}/{{month}}.bean"
    """
  When I run `bean-tw recurring`
  Then the following Beancount file should be updated:
    | Path               | Content                                                                                                                                                                                                                                              |
    | books/2023/02.bean | 2023-02-14 * "Valentine's Day" Expenses:Dining 200\n2023-02-01 * "Monthly Salary" \nAssets:Bank:Checking 50000.00 TWD \n Income:Salary -50000.00 TWD\n2023-02-05 * "Rent Payment" \nAssets:Bank:Checking 15000.00 TWD \n Expenses:Rent -15000.00 TWD |

Scenario: No recurring transactions to add
  Given the following Beancount file exists:
    | Path                | Content                                    |
    | books/2023/03.bean | 2023-03-10 * "Birthday" Expenses:Gifts 300 |
  And the current date is "2023-03-15"
  And the following recurring transaction configuration exists:
    """yaml
    recurring_transactions:
      - description: "Monthly Salary"
        amount: 50000
        currency: TWD
        source_account: Income:Salary
        target_account: Assets:Bank:Checking
        frequency: monthly
        start_date: "2023-01-01"
        book: "books/{{year}}/{{month}}.bean"
    """
  When I run `bean-tw recurring`
  Then the following Beancount file should remain unchanged:
    | Path               | Content                                    |
    | books/2023/03.bean | 2023-03-10 * "Birthday" Expenses:Gifts 300 |

Scenario: Never duplicate recurring transactions
  Given the following Beancount file exists:
    | Path               | Content                                                                                          |
    | books/2023/04.bean | 2023-04-01 * "Monthly Salary" \nAssets:Bank:Checking 50000.00 TWD \n Income:Salary -50000.00 TWD |
  And the current date is "2023-04-10"
  And the following recurring transaction configuration exists:
    """yaml
    recurring_transactions:
      - description: "Monthly Salary"
        amount: 50000
        currency: TWD
        source_account: Income:Salary
        target_account: Assets:Bank:Checking
        frequency: monthly
        start_date: "2023-01-01"
        book: "books/{{year}}/{{month}}.bean"
    """
  When I run `bean-tw recurring`
  Then the following Beancount file should remain unchanged:
    | Path               | Content                                                                                                                                    |
    | books/2023/04.bean | 2023-04-01 * "Monthly Salary" \nAssets:Bank:Checking 50000.00 TWD \n Income:Salary -50000.00 TWD |

Scenario: Only next occurrence of recurring transaction is added
  Given the following Beancount file exists:
    | Path               | Content                                                                                          |
    | books/2023/05.bean | 2023-05-01 * "Monthly Salary" \nAssets:Bank:Checking 50000.00 TWD \n Income:Salary -50000.00 TWD |
  And the current date is "2023-06-02"
  And the following recurring transaction configuration exists:
    """yaml
    recurring_transactions:
      - description: "Monthly Salary"
        amount: 50000
        currency: TWD
        source_account: Income:Salary
        target_account: Assets:Bank:Checking
        frequency: monthly
        start_date: "2023-01-01"
        book: "books/{{year}}/{{month}}.bean"
    """
  When I run `bean-tw recurring`
  Then the following Beancount file should be updated:
    | Path               | Content                                                                                          |
    | books/2023/06.bean | 2023-06-01 * "Monthly Salary" \nAssets:Bank:Checking 50000.00 TWD \n Income:Salary -50000.00 TWD |
```
