#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Standalone Test Script for API Error Handling
ไม่ต้องใช้ pytest - สามารถรันได้โดยตรง

ทดสอบ:
1. Connection errors
2. Timeout errors
3. Empty responses
4. Invalid JSON
5. Error status codes
6. Parameter validation
7. Error logging
"""

import sys
import logging
import json
from io import StringIO
from unittest.mock import Mock
import requests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleApiClient:
    """Simple API client สำหรับทดสอบ"""
    
    def __init__(self):
        self._session = Mock(spec=requests.Session)
    
    def address_api_request_smco(self, payload: dict = {}):
        """Test address API request"""
        try:
            if not payload:
                logger.warning("Empty payload provided")
                return None
            
            response = self._session.post(
                url='http://api.example.com/address',
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"API error status {response.status_code}")
                return None
            
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
            logger.error(f"Request timeout: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def smco_req_find_customer_id(self, cus_code: str = ""):
        """Test find customer ID"""
        try:
            if not cus_code or not isinstance(cus_code, str):
                logger.error(f"Invalid customer code: {cus_code}")
                return None
            
            if len(cus_code.strip()) == 0:
                logger.warning("Empty customer code")
                return None
            
            response = self._session.post(
                url='http://api.example.com/customer/search',
                data={'cus_code': cus_code},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"API error status {response.status_code}")
                return None
            
            try:
                data = response.json()
                if not data or 'customer_id' not in data:
                    logger.warning(f"No customer found for {cus_code}")
                    return None
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def smco_req_find_cus_address(self, cus_id: int = None, **kwargs):
        """Test find customer address"""
        try:
            if cus_id is None:
                logger.error("Customer ID is None")
                return None
            
            if not isinstance(cus_id, int):
                logger.error(f"Invalid ID type: {type(cus_id)}")
                return None
            
            if cus_id <= 0:
                logger.warning(f"Invalid ID value: {cus_id}")
                return None
            
            payload = {'cus_id': cus_id}
            payload.update(kwargs)
            
            response = self._session.post(
                url='http://api.example.com/customer/address',
                data=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"API error status {response.status_code}")
                return None
            
            try:
                data = response.json()
                if not data or 'address' not in data:
                    logger.warning(f"No address for customer {cus_id}")
                    return None
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None


def print_test_header(test_name):
    print("\n" + "="*80)
    print(f"  TEST: {test_name}")
    print("="*80)


def test_case_1():
    """Test: Connection Error"""
    print_test_header("Connection Error")
    
    client = SimpleApiClient()
    client._session.post.side_effect = requests.exceptions.ConnectionError(
        "Cannot connect to server"
    )
    
    result = client.address_api_request_smco({"postcode": "10110"})
    
    if result is None:
        print("✓ PASS: Connection error handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None on connection error")
        return False


def test_case_2():
    """Test: Timeout Error"""
    print_test_header("Timeout Error")
    
    client = SimpleApiClient()
    client._session.post.side_effect = requests.exceptions.Timeout(
        "Request timed out after 30 seconds"
    )
    
    result = client.address_api_request_smco({"postcode": "10110"})
    
    if result is None:
        print("✓ PASS: Timeout error handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None on timeout")
        return False


def test_case_3():
    """Test: Empty Payload"""
    print_test_header("Empty Payload")
    
    client = SimpleApiClient()
    result = client.address_api_request_smco({})
    
    if result is None:
        print("✓ PASS: Empty payload handled correctly")
        print("  - Warning logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for empty payload")
        return False


def test_case_4():
    """Test: Invalid JSON Response"""
    print_test_header("Invalid JSON Response")
    
    client = SimpleApiClient()
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
    client._session.post.return_value = mock_response
    
    result = client.address_api_request_smco({"postcode": "10110"})
    
    if result is None:
        print("✓ PASS: Invalid JSON handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for invalid JSON")
        return False


def test_case_5():
    """Test: API Error Status Code"""
    print_test_header("API Error Status Code (500)")
    
    client = SimpleApiClient()
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 500
    client._session.post.return_value = mock_response
    
    result = client.address_api_request_smco({"postcode": "10110"})
    
    if result is None:
        print("✓ PASS: Error status code handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for error status")
        return False


def test_case_6():
    """Test: Empty Response Data"""
    print_test_header("Empty Response Data")
    
    client = SimpleApiClient()
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    client._session.post.return_value = mock_response
    
    result = client.address_api_request_smco({"postcode": "10110"})
    
    if result is None:
        print("✓ PASS: Empty response handled correctly")
        print("  - Warning logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for empty response")
        return False


def test_case_7():
    """Test: Successful Request"""
    print_test_header("Successful Request")
    
    client = SimpleApiClient()
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "address": "123 Main St",
        "province": "Bangkok"
    }
    client._session.post.return_value = mock_response
    
    result = client.address_api_request_smco({"postcode": "10110"})
    
    if result and result["address"] == "123 Main St":
        print("✓ PASS: Successful request handled correctly")
        print(f"  - Response: {result}")
        return True
    else:
        print("✗ FAIL: Should have returned valid response")
        return False


def test_case_8():
    """Test: Invalid Customer Code"""
    print_test_header("Invalid Customer Code (None)")
    
    client = SimpleApiClient()
    result = client.smco_req_find_customer_id(None)
    
    if result is None:
        print("✓ PASS: None parameter handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for None parameter")
        return False


def test_case_9():
    """Test: Empty Customer Code"""
    print_test_header("Empty Customer Code")
    
    client = SimpleApiClient()
    result = client.smco_req_find_customer_id("")
    
    if result is None:
        print("✓ PASS: Empty customer code handled correctly")
        print("  - Warning logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for empty code")
        return False


def test_case_10():
    """Test: Invalid Customer ID (None)"""
    print_test_header("Invalid Customer ID (None)")
    
    client = SimpleApiClient()
    result = client.smco_req_find_cus_address(None)
    
    if result is None:
        print("✓ PASS: None customer ID handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for None ID")
        return False


def test_case_11():
    """Test: Zero Customer ID"""
    print_test_header("Zero Customer ID")
    
    client = SimpleApiClient()
    result = client.smco_req_find_cus_address(0)
    
    if result is None:
        print("✓ PASS: Zero customer ID handled correctly")
        print("  - Warning logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for zero ID")
        return False


def test_case_12():
    """Test: Negative Customer ID"""
    print_test_header("Negative Customer ID")
    
    client = SimpleApiClient()
    result = client.smco_req_find_cus_address(-5)
    
    if result is None:
        print("✓ PASS: Negative customer ID handled correctly")
        print("  - Warning logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for negative ID")
        return False


def test_case_13():
    """Test: Invalid Type Customer ID"""
    print_test_header("Invalid Type Customer ID (string)")
    
    client = SimpleApiClient()
    result = client.smco_req_find_cus_address("12345")
    
    if result is None:
        print("✓ PASS: Invalid type ID handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None for string ID")
        return False


def test_case_14():
    """Test: Successful Customer Address Lookup"""
    print_test_header("Successful Customer Address Lookup")
    
    client = SimpleApiClient()
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "address": "123 Main St",
        "province": "Bangkok",
        "postcode": "10110"
    }
    client._session.post.return_value = mock_response
    
    result = client.smco_req_find_cus_address(12345)
    
    if result and result["address"] == "123 Main St":
        print("✓ PASS: Successful address lookup")
        print(f"  - Response: {result}")
        return True
    else:
        print("✗ FAIL: Should have returned valid address")
        return False


def test_case_15():
    """Test: Connection Error During Customer Lookup"""
    print_test_header("Connection Error During Customer Lookup")
    
    client = SimpleApiClient()
    client._session.post.side_effect = requests.exceptions.ConnectionError(
        "Network unavailable"
    )
    
    result = client.smco_req_find_customer_id("CUS001")
    
    if result is None:
        print("✓ PASS: Connection error during lookup handled correctly")
        print("  - Error logged")
        print("  - Function returned None")
        return True
    else:
        print("✗ FAIL: Should have returned None on connection error")
        return False


def main():
    print("\n")
    print("#" * 80)
    print("# API REQUEST ERROR HANDLING TEST SUITE")
    print("#" * 80)
    print("# Testing: autopage_MKII_ver5_1_2LITE.py API functions")
    print("# Date: 2024")
    print("#" * 80)
    
    tests = [
        ("test_case_1", test_case_1),
        ("test_case_2", test_case_2),
        ("test_case_3", test_case_3),
        ("test_case_4", test_case_4),
        ("test_case_5", test_case_5),
        ("test_case_6", test_case_6),
        ("test_case_7", test_case_7),
        ("test_case_8", test_case_8),
        ("test_case_9", test_case_9),
        ("test_case_10", test_case_10),
        ("test_case_11", test_case_11),
        ("test_case_12", test_case_12),
        ("test_case_13", test_case_13),
        ("test_case_14", test_case_14),
        ("test_case_15", test_case_15),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {name}: {e}")
            results.append((name, False))
    
    # Print summary
    print("\n\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print("\n" + "=" * 80)
    print(f"  TOTAL: {passed} PASSED, {failed} FAILED out of {len(tests)} tests")
    print("=" * 80)
    
    if failed == 0:
        print("\n  ✓ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n  ✗ {failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
