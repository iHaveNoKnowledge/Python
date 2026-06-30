# autopageMKII Tests

## Quick Start

```bash
# Run all tests (Production mode - no real receipts)
cd C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII
pytest tests/ -v --tb=short

# Run tests on UAT (allow real receipts)
pytest tests/ -v --tb=short --env=uat --allow-receipt

# Run tests on Production (no receipt issuance allowed)
pytest tests/ -v --tb=short --env=prod
```

## Test Structure

- `conftest.py` - pytest fixtures and configuration
- `test_smco_api_client.py` - API client tests
- `test_bot_pos.py` - Bot_POS class tests
- `test_web_journey.py` - Web journey/flow tests
- `test_order_management.py` - Order management tests
- `test_customer_management.py` - Customer management tests
- `test_product_management.py` - Product management tests
- `test_invoice_printing.py` - Invoice printing tests (UAT only)
- `test_tax_information.py` - Tax information tests
- `test_serial_management.py` - Serial number management tests

## Test Data

Test data is loaded from:
`C:\Users\Satawad_Ta\Downloads\Order.toship.20260623_20260630.xlsx`

This file contains 443 rows of order data with 76 columns including:
- Order information (order number, status, dates)
- Customer information (name, address, phone)
- Product information (SKU, name, price)
- Tax information (tax ID, invoice details)

### Available Fixtures

- `test_data` - Full DataFrame from the Excel file
- `sample_order` - Single order row
- `sample_orders` - First 5 orders
- `orders_by_status` - Orders grouped by status

## Safety Notes

- **Production**: Receipt issuance is NOT allowed
- **UAT**: Receipt issuance is allowed with `--allow-receipt` flag
- Always use test data that won't affect real accounts
