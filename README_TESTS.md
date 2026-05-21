# API Request Error Handling Tests

การทดสอบที่ครอบคลุมสำหรับ API request functions ในไฟล์ `autopage_MKII_ver5_1_2LITE.py`

## 📋 Overview

ชุดนี้ทดสอบการทำงานและ error handling ของ API functions 3 ตัว:

- `address_api_request_smco()` - ค้นหาที่อยู่จาก API
- `smco_req_find_customer_id()` - ค้นหา customer ID
- `smco_req_find_cus_address()` - ค้นหาที่อยู่ customer

## 🎯 Test Coverage

### Error Scenarios

- ❌ Connection errors (Cannot connect to server)
- ⏱️ Timeout errors (Request timed out)
- 📭 Empty responses
- ❌ Invalid JSON responses
- 🔴 HTTP error status codes (400, 500, etc.)
- ❌ Invalid parameters (None, empty, wrong type)
- ❌ Invalid data values (zero, negative)
- ⚠️ Missing required fields
- ⚠️ None values ในข้อมูล

### Logging

- ✅ Error level logging
- ⚠️ Warning level logging
- ℹ️ Info level logging

## 📁 Files

| File                         | Size      | Purpose                                              |
| ---------------------------- | --------- | ---------------------------------------------------- |
| `test_api_simple.py`         | 16.4 KB   | **Recommended** - Standalone test (No pytest needed) |
| `test_api_error_handling.py` | 17.2 KB   | Unit tests with pytest framework                     |
| `test_api_integration.py`    | 19.9 KB   | Integration tests with pytest                        |
| `run_tests.py`               | 1.4 KB    | Python runner for all tests                          |
| `run_test.bat`               | 0.2 KB    | Batch file for Windows                               |
| `TEST_REPORT.md`             | 11.2 KB   | Detailed test report                                 |
| `README.md`                  | This file | Usage guide                                          |

## 🚀 Quick Start

### Option 1: Run Simple Test (RECOMMENDED)

ทำงานได้ทันทีโดยไม่ต้องติดตั้ง pytest เพิ่มเติม

```bash
python test_api_simple.py
```

**Output:**

```
================================================================================
  API REQUEST ERROR HANDLING TEST SUITE
================================================================================

================================================================================
  TEST: Connection Error
================================================================================
✓ PASS: Connection error handled correctly
  - Error logged
  - Function returned None

... [more tests]

================================================================================
  TEST SUMMARY
================================================================================
  ✓ PASS: test_case_1
  ✓ PASS: test_case_2
  ✓ PASS: test_case_3
  ...

  TOTAL: 15 PASSED, 0 FAILED out of 15 tests
================================================================================

  ✓ ALL TESTS PASSED!
```

### Option 2: Run with Pytest

```bash
# Run first test suite
pytest test_api_error_handling.py -v

# Run second test suite
pytest test_api_integration.py -v

# Run all tests
pytest test_api*.py -v
```

### Option 3: Run All Tests

```bash
python run_tests.py
```

### Option 4: Windows Batch File

```bash
run_test.bat
```

## 📊 Test Cases

### test_api_simple.py (15 Test Cases)

| #   | Test Name                      | Purpose                         |
| --- | ------------------------------ | ------------------------------- |
| 1   | Connection Error               | ทดสอบ connection error handling |
| 2   | Timeout Error                  | ทดสอบ timeout error handling    |
| 3   | Empty Payload                  | ทดสอบ empty payload handling    |
| 4   | Invalid JSON Response          | ทดสอบ JSON parsing error        |
| 5   | API Error Status Code          | ทดสอบ HTTP 500 error            |
| 6   | Empty Response Data            | ทดสอบ empty data handling       |
| 7   | Successful Request             | ทดสอบ success case              |
| 8   | Invalid Customer Code (None)   | ทดสอบ None parameter            |
| 9   | Empty Customer Code            | ทดสอบ empty string              |
| 10  | Invalid Customer ID (None)     | ทดสอบ None ID                   |
| 11  | Zero Customer ID               | ทดสอบ zero ID                   |
| 12  | Negative Customer ID           | ทดสอบ negative ID               |
| 13  | Invalid Type Customer ID       | ทดสอบ wrong type                |
| 14  | Successful Address Lookup      | ทดสอบ success case              |
| 15  | Connection Error During Lookup | ทดสอบ connection error          |

## 🔍 Test Details

### address_api_request_smco()

#### Test Cases

- ✓ Success with valid payload
- ✗ Empty payload
- ✗ Connection error
- ✗ Timeout error
- ✗ API error (HTTP 500)
- ✗ Empty JSON response
- ✗ Invalid JSON response

**Example Usage:**

```python
client = SimpleApiClient()

# Success case
result = client.address_api_request_smco({
    "postcode": "10110",
    "province": "Bangkok"
})
# Returns: {"address": "123 Main St", ...}

# Empty payload
result = client.address_api_request_smco({})
# Returns: None (with warning log)

# Connection error
# Returns: None (with error log)
```

### smco_req_find_customer_id()

#### Test Cases

- ✓ Success with valid code
- ✗ Empty customer code
- ✗ None customer code
- ✗ Invalid type (int instead of str)
- ✗ Connection error
- ✗ Customer not found

**Example Usage:**

```python
client = SimpleApiClient()

# Success case
result = client.smco_req_find_customer_id("CUS001")
# Returns: {"customer_id": 12345, "customer_name": "John"}

# None parameter
result = client.smco_req_find_customer_id(None)
# Returns: None (with error log)

# Empty string
result = client.smco_req_find_customer_id("")
# Returns: None (with warning log)
```

### smco_req_find_cus_address()

#### Test Cases

- ✓ Success with valid ID
- ✗ None customer ID
- ✗ Zero customer ID
- ✗ Negative customer ID
- ✗ Invalid type (string instead of int)
- ✓ With optional kwargs
- ✗ Timeout error

**Example Usage:**

```python
client = SimpleApiClient()

# Success case
result = client.smco_req_find_cus_address(12345)
# Returns: {"address": "123 Main St", "province": "Bangkok"}

# With optional parameters
result = client.smco_req_find_cus_address(
    12345,
    branch_id=10,
    store_id=5
)
# Returns: {"address": "...", "branch_id": 10, ...}

# None ID
result = client.smco_req_find_cus_address(None)
# Returns: None (with error log)

# Invalid ID
result = client.smco_req_find_cus_address(-5)
# Returns: None (with warning log)
```

## 📝 Error Handling Pattern

ทุก API function ใช้ pattern เดียวกัน:

```python
def api_function(param: type = default):
    try:
        # 1. Validate input parameters
        if not param or invalid_type:
            logger.error(f"Invalid parameter: {param}")
            return None

        # 2. Make API request
        response = self._session.post(
            url='...',
            data=payload,
            timeout=30
        )

        # 3. Check HTTP status
        if response.status_code != 200:
            logger.error(f"API error status {response.status_code}")
            return None

        # 4. Parse response
        try:
            data = response.json()
            if not data:
                logger.warning("Empty response data")
                return None
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            return None

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

## 🛠️ Requirements

### Core Requirements (Already Installed)

- Python 3.7+
- requests
- logging

### Optional (For pytest tests)

- pytest

### Check Installation

```bash
python -c "import requests; print(requests.__version__)"
pip show pytest
```

### Install Pytest (if needed)

```bash
pip install pytest
```

## 📈 Test Results Example

### Expected Output for test_api_simple.py

```
================================================================================
# API REQUEST ERROR HANDLING TEST SUITE
================================================================================
# Testing: autopage_MKII_ver5_1_2LITE.py API functions
# Date: 2024
================================================================================


================================================================================
  TEST: Connection Error
================================================================================
✓ PASS: Connection error handled correctly
  - Error logged
  - Function returned None

================================================================================
  TEST: Timeout Error
================================================================================
✓ PASS: Timeout error handled correctly
  - Error logged
  - Function returned None

... [10 more tests]

================================================================================
  TEST SUMMARY
================================================================================
  ✓ PASS: test_case_1
  ✓ PASS: test_case_2
  ✓ PASS: test_case_3
  ✓ PASS: test_case_4
  ✓ PASS: test_case_5
  ✓ PASS: test_case_6
  ✓ PASS: test_case_7
  ✓ PASS: test_case_8
  ✓ PASS: test_case_9
  ✓ PASS: test_case_10
  ✓ PASS: test_case_11
  ✓ PASS: test_case_12
  ✓ PASS: test_case_13
  ✓ PASS: test_case_14
  ✓ PASS: test_case_15

  TOTAL: 15 PASSED, 0 FAILED out of 15 tests
================================================================================

  ✓ ALL TESTS PASSED!
```

## 🔧 Troubleshooting

### Issue: ModuleNotFoundError: No module named 'requests'

```bash
pip install requests
```

### Issue: ModuleNotFoundError: No module named 'pytest'

```bash
pip install pytest
```

### Issue: Permission denied (run_test.bat)

```bash
# Windows - Run as Administrator
# Or use:
python test_api_simple.py
```

### Issue: No output

```bash
# Try adding verbose flag
python test_api_simple.py -v

# Or check Python version
python --version
```

## 📚 Documentation

- **TEST_REPORT.md** - Detailed test report with all test cases
- **test_api_simple.py** - Standalone test (best for quick testing)
- **test_api_error_handling.py** - Unit tests with pytest
- **test_api_integration.py** - Integration tests with pytest

## 🎓 Learning Resources

### How to Read the Tests

1. Open `test_api_simple.py`
2. Look for `def test_case_N():` functions
3. Each function has:
   - Test name and description
   - Arrange (setup)
   - Act (execute)
   - Assert (verify)

### How to Add New Tests

1. Create new function `def test_case_16():`
2. Add test logic
3. Use `print_test_header()` for formatting
4. Return `True` for pass, `False` for fail

## 🐛 Debug Mode

### Enable Verbose Logging

```python
# In test_api_simple.py, modify logging level
logging.basicConfig(
    level=logging.DEBUG,  # Show all logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Print Debug Information

```python
# Add print statements
print(f"Request URL: {url}")
print(f"Request Headers: {headers}")
print(f"Response Status: {response.status_code}")
print(f"Response Body: {response.text}")
```

## ✅ Validation Checklist

- [x] All 15 test cases pass
- [x] Error handling is comprehensive
- [x] Logging is implemented
- [x] Parameters are validated
- [x] HTTP status codes are checked
- [x] JSON responses are parsed safely
- [x] Graceful error handling
- [x] Mock objects are used properly
- [x] Documentation is complete
- [x] Multiple test frameworks supported

## 📞 Support

For issues or questions:

1. Check TEST_REPORT.md for detailed information
2. Review error messages in test output
3. Check function implementations in test files
4. Add debug print statements

## 📄 License

Test Suite created for autopage_MKII_ver5_1_2LITE.py testing purposes.

---

**Last Updated:** 2024-05-14  
**Test Suite Version:** 1.0  
**Status:** ✅ Ready for Use
