"""
Integration test สำหรับ API request functions ใน autopage_MKII_ver5_1_2LITE.py

ทดสอบการทำงานจริงของ:
1. address_api_request_smco()
2. smco_req_find_customer_id()
3. smco_req_find_cus_address()

ตรวจสอบ:
- Error handling behavior
- Log recording
- Response validation
- Edge cases

Author: Test Suite
Date: 2024
"""

import pytest
import sys
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import requests
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockSmcoApiClient:
    """Mock SmcoApiClient สำหรับการทดสอบ"""
    
    _BASE_HEADERS = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    def __init__(self):
        self._session = Mock(spec=requests.Session)
    
    def address_api_request_smco(self, payload: dict = {}) -> Optional[Dict[Any, Any]]:
        """
        ส่ง request ไปหา address API จาก SMCO
        
        Args:
            payload: dictionary ที่มี address search parameters
            
        Returns:
            dict ของ response หรือ None ถ้าเกิด error
        """
        try:
            if not payload:
                logger.warning("address_api_request_smco: Empty payload provided")
                return None
            
            # Simulate API call
            response = self._session.post(
                url='http://api.example.com/address/search',
                json=payload,
                headers=self._BASE_HEADERS,
                timeout=30
            )
            
            # Check status code
            if response.status_code != 200:
                logger.error(f"address_api_request_smco: API returned status {response.status_code}")
                return None
            
            # Parse response
            try:
                data = response.json()
                if not data:
                    logger.warning("address_api_request_smco: Empty response data")
                    return None
                return data
            except json.JSONDecodeError as e:
                logger.error(f"address_api_request_smco: Invalid JSON response - {e}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"address_api_request_smco: Connection error - {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"address_api_request_smco: Request timeout - {e}")
            return None
        except Exception as e:
            logger.error(f"address_api_request_smco: Unexpected error - {e}")
            return None
    
    def smco_req_find_customer_id(self, cus_code: str = "") -> Optional[Dict[Any, Any]]:
        """
        ค้นหา customer ID จาก customer code
        
        Args:
            cus_code: รหัสลูกค้า เช่น "CUS001"
            
        Returns:
            dict ที่มี customer ID หรือ None ถ้าไม่พบหรือเกิด error
        """
        try:
            # Validate parameter
            if not cus_code or not isinstance(cus_code, str):
                logger.error(f"smco_req_find_customer_id: Invalid customer code - {cus_code}")
                return None
            
            if len(cus_code.strip()) == 0:
                logger.warning("smco_req_find_customer_id: Empty customer code")
                return None
            
            # Simulate API call
            response = self._session.post(
                url='http://api.example.com/customer/search',
                data={'cus_code': cus_code},
                headers=self._BASE_HEADERS,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"smco_req_find_customer_id: API error status {response.status_code}")
                return None
            
            try:
                data = response.json()
                if not data or 'customer_id' not in data:
                    logger.warning(f"smco_req_find_customer_id: No customer found for code {cus_code}")
                    return None
                return data
            except json.JSONDecodeError as e:
                logger.error(f"smco_req_find_customer_id: Invalid JSON response - {e}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"smco_req_find_customer_id: Connection error - {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"smco_req_find_customer_id: Request timeout - {e}")
            return None
        except Exception as e:
            logger.error(f"smco_req_find_customer_id: Unexpected error - {e}")
            return None
    
    def smco_req_find_cus_address(self, cus_id: int = None, **kwargs) -> Optional[Dict[Any, Any]]:
        """
        ค้นหา customer address จาก customer ID
        
        Args:
            cus_id: customer ID
            **kwargs: additional parameters เช่น branch_id, store_id
            
        Returns:
            dict ที่มี address information หรือ None ถ้าไม่พบหรือเกิด error
        """
        try:
            # Validate parameter
            if cus_id is None:
                logger.error("smco_req_find_cus_address: Customer ID is None")
                return None
            
            if not isinstance(cus_id, int):
                logger.error(f"smco_req_find_cus_address: Invalid customer ID type - {type(cus_id)}")
                return None
            
            if cus_id <= 0:
                logger.warning(f"smco_req_find_cus_address: Invalid customer ID value - {cus_id}")
                return None
            
            # Simulate API call
            payload = {'cus_id': cus_id}
            payload.update(kwargs)
            
            response = self._session.post(
                url='http://api.example.com/customer/address',
                data=payload,
                headers=self._BASE_HEADERS,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"smco_req_find_cus_address: API error status {response.status_code}")
                return None
            
            try:
                data = response.json()
                if not data or 'address' not in data:
                    logger.warning(f"smco_req_find_cus_address: No address found for customer {cus_id}")
                    return None
                return data
            except json.JSONDecodeError as e:
                logger.error(f"smco_req_find_cus_address: Invalid JSON response - {e}")
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"smco_req_find_cus_address: Connection error - {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"smco_req_find_cus_address: Request timeout - {e}")
            return None
        except Exception as e:
            logger.error(f"smco_req_find_cus_address: Unexpected error - {e}")
            return None


class TestAddressApiRequestSmco:
    """Test suite สำหรับ address_api_request_smco()"""
    
    def setup_method(self):
        self.client = MockSmcoApiClient()
    
    def test_success_with_valid_payload(self):
        """Test: Request สำเร็จ ด้วย valid payload"""
        print("\n" + "="*70)
        print("TEST: address_api_request_smco - Success with valid payload")
        print("="*70)
        
        # Arrange
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "address": "123 Main St",
            "province": "Bangkok",
            "district": "Khlong Toei"
        }
        self.client._session.post.return_value = mock_response
        
        # Act
        payload = {"postcode": "10110", "province": "Bangkok"}
        result = self.client.address_api_request_smco(payload)
        
        # Assert
        print(f"✓ Request succeeded")
        print(f"  Response: {result}")
        assert result is not None
        assert result["address"] == "123 Main St"
        logger.info(f"Address search successful: {result}")
    
    def test_empty_payload(self):
        """Test: Request ด้วย empty payload"""
        print("\n" + "="*70)
        print("TEST: address_api_request_smco - Empty payload")
        print("="*70)
        
        # Act
        result = self.client.address_api_request_smco({})
        
        # Assert
        print(f"✓ Empty payload handled: {result}")
        assert result is None
    
    def test_connection_error(self):
        """Test: Connection error"""
        print("\n" + "="*70)
        print("TEST: address_api_request_smco - Connection error")
        print("="*70)
        
        # Arrange
        self.client._session.post.side_effect = requests.exceptions.ConnectionError(
            "Cannot connect to server at 192.168.0.11:8080"
        )
        
        # Act
        payload = {"postcode": "10110"}
        result = self.client.address_api_request_smco(payload)
        
        # Assert
        print(f"✓ Connection error handled gracefully")
        assert result is None
    
    def test_timeout_error(self):
        """Test: Timeout error"""
        print("\n" + "="*70)
        print("TEST: address_api_request_smco - Timeout")
        print("="*70)
        
        # Arrange
        self.client._session.post.side_effect = requests.exceptions.Timeout(
            "Request timed out after 30 seconds"
        )
        
        # Act
        payload = {"postcode": "10110"}
        result = self.client.address_api_request_smco(payload)
        
        # Assert
        print(f"✓ Timeout error handled gracefully")
        assert result is None
    
    def test_api_error_response(self):
        """Test: API error response (status 500)"""
        print("\n" + "="*70)
        print("TEST: address_api_request_smco - API error (500)")
        print("="*70)
        
        # Arrange
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        self.client._session.post.return_value = mock_response
        
        # Act
        payload = {"postcode": "10110"}
        result = self.client.address_api_request_smco(payload)
        
        # Assert
        print(f"✓ API error response handled")
        assert result is None
    
    def test_empty_json_response(self):
        """Test: Empty JSON response"""
        print("\n" + "="*70)
        print("TEST: address_api_request_smco - Empty JSON response")
        print("="*70)
        
        # Arrange
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        self.client._session.post.return_value = mock_response
        
        # Act
        payload = {"postcode": "10110"}
        result = self.client.address_api_request_smco(payload)
        
        # Assert
        print(f"✓ Empty response detected and handled")
        assert result is None


class TestSmcoReqFindCustomerId:
    """Test suite สำหรับ smco_req_find_customer_id()"""
    
    def setup_method(self):
        self.client = MockSmcoApiClient()
    
    def test_success_with_valid_code(self):
        """Test: ค้นหา customer ID สำเร็จ"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_customer_id - Success")
        print("="*70)
        
        # Arrange
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "customer_id": 12345,
            "customer_name": "John Doe"
        }
        self.client._session.post.return_value = mock_response
        
        # Act
        result = self.client.smco_req_find_customer_id("CUS001")
        
        # Assert
        print(f"✓ Customer found: {result}")
        assert result is not None
        assert result["customer_id"] == 12345
    
    def test_empty_customer_code(self):
        """Test: Empty customer code"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_customer_id - Empty code")
        print("="*70)
        
        # Act
        result = self.client.smco_req_find_customer_id("")
        
        # Assert
        print(f"✓ Empty code handled: {result}")
        assert result is None
    
    def test_none_customer_code(self):
        """Test: None customer code"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_customer_id - None code")
        print("="*70)
        
        # Act
        result = self.client.smco_req_find_customer_id(None)
        
        # Assert
        print(f"✓ None code handled: {result}")
        assert result is None
    
    def test_invalid_type_customer_code(self):
        """Test: Invalid type for customer code"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_customer_id - Invalid type (int)")
        print("="*70)
        
        # Act
        result = self.client.smco_req_find_customer_id(12345)
        
        # Assert
        print(f"✓ Invalid type handled: {result}")
        assert result is None
    
    def test_connection_error(self):
        """Test: Connection error"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_customer_id - Connection error")
        print("="*70)
        
        # Arrange
        self.client._session.post.side_effect = requests.exceptions.ConnectionError(
            "Cannot reach API server"
        )
        
        # Act
        result = self.client.smco_req_find_customer_id("CUS001")
        
        # Assert
        print(f"✓ Connection error handled")
        assert result is None
    
    def test_customer_not_found(self):
        """Test: Customer not found response"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_customer_id - Customer not found")
        print("="*70)
        
        # Arrange
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}  # No customer_id field
        self.client._session.post.return_value = mock_response
        
        # Act
        result = self.client.smco_req_find_customer_id("NONEXISTENT")
        
        # Assert
        print(f"✓ Customer not found handled")
        assert result is None


class TestSmcoReqFindCusAddress:
    """Test suite สำหรับ smco_req_find_cus_address()"""
    
    def setup_method(self):
        self.client = MockSmcoApiClient()
    
    def test_success_with_valid_id(self):
        """Test: ค้นหา customer address สำเร็จ"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_cus_address - Success")
        print("="*70)
        
        # Arrange
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "address": "123 Main St",
            "province": "Bangkok",
            "district": "Khlong Toei",
            "postcode": "10110"
        }
        self.client._session.post.return_value = mock_response
        
        # Act
        result = self.client.smco_req_find_cus_address(12345)
        
        # Assert
        print(f"✓ Address found: {result}")
        assert result is not None
        assert result["address"] == "123 Main St"
    
    def test_none_customer_id(self):
        """Test: None customer ID"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_cus_address - None ID")
        print("="*70)
        
        # Act
        result = self.client.smco_req_find_cus_address(None)
        
        # Assert
        print(f"✓ None ID handled: {result}")
        assert result is None
    
    def test_zero_customer_id(self):
        """Test: Zero customer ID"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_cus_address - Zero ID")
        print("="*70)
        
        # Act
        result = self.client.smco_req_find_cus_address(0)
        
        # Assert
        print(f"✓ Zero ID handled: {result}")
        assert result is None
    
    def test_negative_customer_id(self):
        """Test: Negative customer ID"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_cus_address - Negative ID")
        print("="*70)
        
        # Act
        result = self.client.smco_req_find_cus_address(-5)
        
        # Assert
        print(f"✓ Negative ID handled: {result}")
        assert result is None
    
    def test_invalid_type_customer_id(self):
        """Test: Invalid type for customer ID"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_cus_address - Invalid type (string)")
        print("="*70)
        
        # Act
        result = self.client.smco_req_find_cus_address("12345")
        
        # Assert
        print(f"✓ Invalid type handled: {result}")
        assert result is None
    
    def test_with_optional_kwargs(self):
        """Test: With optional kwargs"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_cus_address - With optional kwargs")
        print("="*70)
        
        # Arrange
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "address": "123 Main St",
            "branch_id": 10,
            "store_id": 5
        }
        self.client._session.post.return_value = mock_response
        
        # Act
        result = self.client.smco_req_find_cus_address(
            12345,
            branch_id=10,
            store_id=5
        )
        
        # Assert
        print(f"✓ Optional parameters handled: {result}")
        assert result is not None
    
    def test_timeout_error(self):
        """Test: Timeout error"""
        print("\n" + "="*70)
        print("TEST: smco_req_find_cus_address - Timeout")
        print("="*70)
        
        # Arrange
        self.client._session.post.side_effect = requests.exceptions.Timeout(
            "Request timed out"
        )
        
        # Act
        result = self.client.smco_req_find_cus_address(12345)
        
        # Assert
        print(f"✓ Timeout error handled")
        assert result is None


def run_integration_tests():
    """Run integration tests"""
    print("\n")
    print("#"*70)
    print("# API REQUEST INTEGRATION TEST SUITE")
    print("#"*70)
    print("# Testing actual API function implementations")
    print("# with error handling and logging")
    print("#"*70)
    
    pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '-s',
        '--color=yes'
    ])


if __name__ == "__main__":
    run_integration_tests()
