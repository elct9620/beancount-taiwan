# HSBC Credit Card Importer

## Motivation

Personally, I use HSBC credit card (Travelers) as my main credit card for now. However, HSBC does not provide any method to export credit card transactions in a machine-readable format (e.g., CSV)

As workaround, I manually copy API response from HSBC card statement page, and keep as raw JSON file. This importer is created to parse such JSON file and convert into Beancount entries.

## Usage

```
bean-tw convert path/to/hsbc_credit_card_statement.json
```

- Returns Beancount entries parsed from the given JSON file to standard output.
- Raises error if the given file is not a valid HSBC credit card statement JSON file.

## Configuration

Each importer has its own config to provide default account mapping or special handling.

```yaml
# config/hsbc_credit_card_importer.yaml
default:
    account:
        credit_card: Liabilities:CreditCard:HSBC:Travelers
        expense: Expenses:Life
        payment_asset: Assets:Bank:Checking

rules:
    - name: foreign_currency_expense
      description_contains: "國外交易手續費"
      expense_account: Expenses:BankFees
    - type: payment
      description_contains: "全國繳費網"
      payment_asset_account: Assets:Bank:PostOffice

cards:
    - name: "Travelers"
      card_no_suffix: "1234"
      accounts:
          credit_card: Liabilities:CreditCard:HSBC:Travelers
          expense: Expenses:Travel
          payment_asset: Assets:Bank:TravelersChecking
    rules:
        - name: foreign_currency_expense
          description_contains: "FOREIGN TRANSACTION FEE"
          expense_account: Expenses:BankFees

```

## Scenarios

```gherkin
Scenario: Import HSBC credit card expense from JSON file
  Given a valid HSBC credit card statement payload saved as `hsbc_statement.json`
  """
  {
    "payload": [
      {
        "amount": "0",
        "description": "TEST TRANSACTION 1",
        "amtCy": "",
        "txnLoc": "",
        "txnDate": "2025/07/29",
        "cyCnvDate": "",
        "postingDate": "2025/08/04",
        "ntdAmount": "699",
        "isForeignTxn": false,
        "isInstallmentTxn": false,
        "cardNo": "1234",
        "relationShip": "P"
      }
    ]
  }
  """
  When I run the convert command on `hsbc_statement.json`
  Then the output should contain Beancount entries representing the transactions in the JSON file
  """
  2025-08-04 * "TEST TRANSACTION 1"
      cardNo: 1234
      tnxDate: 2025-07-29
      Expenses:Life 699.00 TWD
      Liabilities:CreditCard:HSBC:Travelers
  """

Scenario: Import HSBC credit card foreign currency expense from JSON file
  Given a valid HSBC credit card statement payload with foreign currency transaction saved as `hsbc_foreign_currency_statement.json`
  """
  {
    "payload": [
      {
        "amount": "20",
        "description": "FOREIGN TRANSACTION",
        "amtCy": "USD",
        "txnLoc": "USA",
        "txnDate": "2025/07/30",
        "cyCnvDate": "2025/08/01",
        "postingDate": "2025/08/05",
        "ntdAmount": "600",
        "isForeignTxn": true,
        "isInstallmentTxn": false,
        "cardNo": "1234",
        "relationShip": ""
      }
    ]
  }
  """
  When I run the convert command on `hsbc_foreign_currency_statement.json`
  Then the output should contain Beancount entries representing the foreign currency transaction in the JSON file
  """
  2025-08-05 * "FOREIGN TRANSACTION"
      cardNo: 1234
      tnxDate: 2025-07-30
      tnxLoc: USA
      Expenses:Life 20.00 USD @@ 600.00 TWD
      Liabilities:CreditCard:HSBC:Travelers
  """

Scenario: Import HSBC credit card payment transaction from JSON file
  Given a valid HSBC credit card statement payload with payment transaction saved as `hsbc_payment_statement.json`
  """
  {
    "payload": [
      {
        "amount": "0",
        "description": "PAYMENT RECEIVED",
        "amtCy": "",
        "txnLoc": "",
        "txnDate": "2025/07/31",
        "cyCnvDate": "",
        "postingDate": "2025/08/06",
        "ntdAmount": "-5000",
        "isForeignTxn": false,
        "isInstallmentTxn": false,
        "cardNo": "1234",
        "relationShip": ""
      }
    ]
  }
  """
  When I run the convert command on `hsbc_payment_statement.json`
  Then the output should contain Beancount entries representing the payment transaction in the JSON file
  """
  2025-08-06 * "PAYMENT RECEIVED"
      cardNo: 1234
      tnxDate: 2025-07-31
      Liabilities:CreditCard:HSBC:Travelers -5000.00 TWD
      Assets:Bank:Checking
  """

Scenario: Import HSBC credit card foreign transaction fee from JSON file
  Given a valid HSBC credit card statement payload with foreign transaction fee saved as `hsbc_foreign_fee_statement.json`
  """
  {
    "payload": [
      "amount": "0",
      "description": "國外交易手續費",
      "amtCy": "   ",
      "txnLoc": "",
      "txnDate": "2025/09/03",
      "cyCnvDate": "",
      "postingDate": "2025/09/04",
      "ntdAmount": "39",
      "isForeignTxn": false,
      "isInstallmentTxn": false,
      "cardNo": "",
      "relationShip": ""
    ]
  }
  """
  When I run the convert command on `hsbc_foreign_fee_statement.json`
  Then the output should contain Beancount entries representing the foreign transaction fee in the JSON file
  """
  2025-09-04 * "FOREIGN TRANSACTION FEE"
      tnxDate: 2025-09-03
      Expenses:BankFees 39.00 TWD
      Liabilities:CreditCard:HSBC:Travelers
  """


Scenario: Handle invalid HSBC credit card statement JSON file
    Given an invalid HSBC credit card statement payload saved as `invalid_hsbc_statement.json`
    """gherkin
    {
      "invalid_key": []
    }
    """
    When I run the convert command on `invalid_hsbc_statement.json`
    Then an error should be raised indicating the file is not a valid HSBC credit card statement JSON file
```

