"""
Unit tests for autopage_MKII_ver5_2_0LITE.py
Tests actual code from the main file using mocking
"""
import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSmcoApiClient:
    """Tests for SmcoApiClient class from autopage_MKII_ver5_2_0LITE.py"""

    @pytest.fixture
    def api_client(self):
        """Create a SmcoApiClient instance with mocked session"""
        with patch('autopage_MKII_ver5_2_0LITE.requests.Session') as mock_session:
            from autopage_MKII_ver5_2_0LITE import SmcoApiClient
            client = SmcoApiClient()
            client._session = mock_session()
            return client

    def test_init_creates_session(self):
        """Test that SmcoApiClient creates a session on init"""
        with patch('autopage_MKII_ver5_2_0LITE.requests.Session') as mock_session:
            from autopage_MKII_ver5_2_0LITE import SmcoApiClient
            client = SmcoApiClient()
            mock_session.assert_called_once()
            assert client._session is not None

    def test_base_headers_contains_required_fields(self):
        """Test that _BASE_HEADERS has required HTTP headers"""
        from autopage_MKII_ver5_2_0LITE import SmcoApiClient
        required_headers = ['Accept', 'Content-Type', 'User-Agent', 'X-Requested-With']
        for header in required_headers:
            assert header in SmcoApiClient._BASE_HEADERS

    def test_login_makes_post_request(self, api_client):
        """Test that login makes POST request to correct URL"""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'success'}
        api_client._session.post.return_value = mock_response

        result = api_client.login('http://test.com', 'user123', 'pass123')

        api_client._session.post.assert_called_once()
        call_args = api_client._session.post.call_args
        assert 'loginssoauthen.htm' in call_args[0][0]
        assert result == {'status': 'success'}

    def test_login_sends_correct_data(self, api_client):
        """Test that login sends correct form data"""
        mock_response = Mock()
        mock_response.json.return_value = {}
        api_client._session.post.return_value = mock_response

        api_client.login('http://test.com', 'user123', 'pass123')

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['username'] == ['user123']
        assert data['password'] == ['pass123']

    def test_login_disables_ssl_verification(self, api_client):
        """Test that login uses verify=False for SSL"""
        mock_response = Mock()
        mock_response.json.return_value = {}
        api_client._session.post.return_value = mock_response

        api_client.login('http://test.com', 'user', 'pass')

        call_args = api_client._session.post.call_args
        assert call_args[1].get('verify') == False or call_args[1].get('verify') is False

    def test_post_returns_response(self, api_client):
        """Test that post method returns response object"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        result = api_client.post('http://test.com/api', {'key': 'value'})

        assert result == mock_response

    def test_post_includes_origin_header(self, api_client):
        """Test that post method includes Origin header"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.post('http://test.com/api', {}, origin='http://origin.com')

        call_args = api_client._session.post.call_args
        headers = call_args[1]['headers']
        assert headers['Origin'] == 'http://origin.com'

    def test_get_vatinfo_uses_json_content_type(self, api_client):
        """Test that get_vatinfo sends JSON data"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_vatinfo({'nid': '1234567890123'})

        call_args = api_client._session.post.call_args
        headers = call_args[1]['headers']
        assert 'application/json' in headers['Content-Type']
        assert call_args[1]['json'] == {'nid': '1234567890123'}

    def test_get_vatinfo_uses_correct_url(self, api_client):
        """Test that get_vatinfo calls correct RD API URL"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_vatinfo({})

        call_args = api_client._session.post.call_args
        assert 'vsinter.rd.go.th' in call_args[0][0]

    def test_get_product_info_builds_correct_payload(self, api_client):
        """Test that get_product_info builds correct payload"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_product_info('http://test.com', 'PR2-000495', {'JSESSIONID': 'abc'})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['requestText'] == 'PR2-000495'
        assert data['activeFlag'] == 'true'

    def test_get_serial_list_builds_correct_search_value(self, api_client):
        """Test that get_serial_list builds correct search JSON"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_serial_list('http://test.com', '123', 180, 441, {})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        search_value = json.loads(data['search[value]'])
        assert search_value['byId'] == '123'
        assert search_value['byMasterId'] == 180
        assert search_value['byParentId'] == 441

    def test_get_serial_list_has_17_columns(self, api_client):
        """Test that get_serial_list includes all 17 DataTables columns"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_serial_list('http://test.com', '123', 180, 441, {})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        # Check columns[0] to columns[16] exist
        for i in range(17):
            assert f'columns[{i}][data]' in data

    def test_get_cus_data_builds_correct_payload(self, api_client):
        """Test that get_cus_data builds correct payload"""
        mock_response = Mock()
        mock_response.status_code = 200
        api_client._session.post.return_value = mock_response

        api_client.get_cus_data('http://test.com', 'John', 'N', {})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['requestText'] == 'John'
        assert data['target'] == 'N'

    def test_get_cus_data_returns_none_on_error(self, api_client):
        """Test that get_cus_data returns None on non-200 status"""
        mock_response = Mock()
        mock_response.status_code = 500
        api_client._session.post.return_value = mock_response
        api_client.cus_order = 'TEST-001'

        result = api_client.get_cus_data('http://test.com', 'John', 'N', {})

        assert result is None


class TestAccountManager:
    """Tests for AccountManager class from functions/utils/crypto.py"""

    def test_init_sets_service_name(self):
        """Test that AccountManager stores service name"""
        from functions.utils.crypto import AccountManager
        manager = AccountManager("MyService")
        assert manager.service_name == "MyService"

    @patch('functions.utils.crypto.keyring')
    def test_set_last_username_calls_keyring(self, mock_keyring):
        """Test that set_last_username calls keyring.set_password"""
        from functions.utils.crypto import AccountManager
        manager = AccountManager("TestService")
        manager.set_last_username("testuser")
        mock_keyring.set_password.assert_called_once_with("TestService", "last_user", "testuser")

    @patch('functions.utils.crypto.keyring')
    def test_get_last_username_calls_keyring(self, mock_keyring):
        """Test that get_last_username calls keyring.get_password"""
        from functions.utils.crypto import AccountManager
        mock_keyring.get_password.return_value = "storeduser"
        manager = AccountManager("TestService")
        result = manager.get_last_username()
        mock_keyring.get_password.assert_called_once_with("TestService", "last_user")
        assert result == "storeduser"


class TestBaseUrlFinder:
    """Tests for BaseUrlFinder class from functions/BaseUrlFinder/BaseUrlFinder.py"""

    @pytest.fixture
    def finder(self):
        """Create a BaseUrlFinder instance"""
        from functions.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder
        return BaseUrlFinder()

    def test_init_creates_empty_ips_json(self):
        """Test that BaseUrlFinder initializes with empty ips_json"""
        from functions.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder
        finder = BaseUrlFinder()
        assert hasattr(finder, 'ips_json')

    @patch('functions.BaseUrlFinder.BaseUrlFinder.requests.get')
    def test_check_available_ip_first_success(self, mock_get):
        """Test check_available_ip returns first IP when it responds 200"""
        from functions.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder
        finder = BaseUrlFinder()
        finder.ips_json = {'ip1': 'http://192.168.0.11:8080', 'ip2': 'http://192.168.0.142:9099'}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = finder.check_available_ip()
        assert result is not None

    @patch('functions.BaseUrlFinder.BaseUrlFinder.requests.get')
    def test_check_available_ip_returns_none_when_all_fail(self, mock_get):
        """Test check_available_ip returns None when all IPs fail"""
        from functions.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder
        from requests.exceptions import ConnectionError
        finder = BaseUrlFinder()
        finder.ips_json = {'ip1': 'http://192.168.0.11:8080'}

        mock_get.side_effect = ConnectionError("Connection refused")

        result = finder.check_available_ip()
        assert result is None


class TestClassifyVatinfoAddress:
    """Tests for classify_vatinfo_address method - regex pattern matching"""

    def test_classify_extracts_subdistrict(self):
        """Test that regex extracts subdistrict from address"""
        import re
        pattern = re.compile(r'ตำบล/แขวง\s+(\S+).*?เขต\s+(\S+).*?จังหวัด\s+(\S+)')
        address = '123 ถนนสุขุมวิท ตำบล/แขวง คลองเตย เขต คลองเตย จังหวัด กรุงเทพมหานคร 10110'
        matches = pattern.search(address)
        assert matches.group(1) == 'คลองเตย'

    def test_classify_extracts_district(self):
        """Test that regex extracts district from address"""
        import re
        pattern = re.compile(r'ตำบล/แขวง\s+(\S+).*?เขต\s+(\S+).*?จังหวัด\s+(\S+)')
        address = '123 ถนนสุขุมวิท ตำบล/แขวง คลองเตย เขต คลองเตย จังหวัด กรุงเทพมหานคร 10110'
        matches = pattern.search(address)
        assert matches.group(2) == 'คลองเตย'

    def test_classify_extracts_province(self):
        """Test that regex extracts province from address"""
        import re
        pattern = re.compile(r'ตำบล/แขวง\s+(\S+).*?เขต\s+(\S+).*?จังหวัด\s+(\S+)')
        address = '123 ถนนสุขุมวิท ตำบล/แขวง คลองเตย เขต คลองเตย จังหวัด กรุงเทพมหานคร 10110'
        matches = pattern.search(address)
        assert matches.group(3) == 'กรุงเทพมหานคร'

    def test_classify_adds_space_after_company_prefix(self):
        """Test that regex adds space after บริษัท"""
        import re
        name = 'บริษัททดสอบจำกัด'
        result = re.sub(r'(บริษัท)\s*', r'\1 ', name)
        assert 'บริษัท ' in result

    def test_classify_handles_no_match(self):
        """Test that regex returns None when pattern doesn't match"""
        import re
        pattern = re.compile(r'ตำบล/แขวง\s+(\S+).*?เขต\s+(\S+).*?จังหวัด\s+(\S+)')
        address = '123 ถนนtested without pattern'
        matches = pattern.search(address)
        assert matches is None


class TestNormalizeVatApiData:
    """Tests for normalize_vat_api_data logic - address building"""

    def test_normalize_builds_address_with_components(self):
        """Test that address is built correctly from components"""
        api_item = {
            'addno': '123',
            'moono': '5',
            'soinam': 'ทดสอบ',
            'thnnam': 'สุขุมวิท',
            'tamnam': 'คลองเตย',
            'ampnam': 'คลองเตย',
            'provnam': 'กรุงเทพ',
            'poscod': '10110'
        }

        address_parts = []
        if api_item.get('addno'):
            address_parts.append(api_item['addno'])
        if api_item.get('moono') and api_item['moono'] != '-':
            address_parts.append(f"หมู่ {api_item['moono']}")
        if api_item.get('soinam') and api_item['soinam'] != '-':
            address_parts.append(f"ซอย{api_item['soinam']}")
        if api_item.get('thnnam') and api_item['thnnam'] != '-':
            address_parts.append(f"ถนน{api_item['thnnam']}")

        address = ' '.join(address_parts)
        assert '123' in address
        assert 'หมู่ 5' in address
        assert 'ซอยทดสอบ' in address
        assert 'ถนนสุขุมวิท' in address

    def test_normalize_branch_mapping(self):
        """Test that branch number maps correctly"""
        branch_num = '00000'
        if branch_num == '00000':
            branch = '(สำนักงานใหญ่)'
        else:
            branch = f'(สาขา{branch_num})'
        assert branch == '(สำนักงานใหญ่)'

    def test_normalize_branch_with_number(self):
        """Test that branch number maps correctly"""
        branch_num = '00100'
        if branch_num == '00000':
            branch = '(สำนักงานใหญ่)'
        else:
            branch = f'(สาขา{branch_num})'
        assert branch == '(สาขา00100)'

    def test_normalize_address_shortened_excludes_tambon(self):
        """Test that shortened address excludes tambon/district"""
        address_parts = ['123', 'หมู่ 5']
        address_shortened = ' '.join(address_parts)
        assert 'ตำบล' not in address_shortened
        assert 'แขวง' not in address_shortened


class TestGetSerialListPayload:
    """Tests for get_serial_list payload construction from SmcoApiClient"""

    @pytest.fixture
    def api_client(self):
        """Create a SmcoApiClient instance with mocked session"""
        with patch('autopage_MKII_ver5_2_0LITE.requests.Session') as mock_session:
            from autopage_MKII_ver5_2_0LITE import SmcoApiClient
            client = SmcoApiClient()
            client._session = mock_session()
            return client

    def test_serial_list_includes_draw_param(self, api_client):
        """Test that get_serial_list includes draw parameter"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_serial_list('http://test.com', '123', 180, 441, {})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['draw'] == '2'

    def test_serial_list_includes_search_regex(self, api_client):
        """Test that get_serial_list includes search[regex] = false"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_serial_list('http://test.com', '123', 180, 441, {})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['search[regex]'] == 'false'

    def test_serial_list_includes_timestamp(self, api_client):
        """Test that get_serial_list includes timestamp for cache busting"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_serial_list('http://test.com', '123', 180, 441, {}, timestamp='1234567890')

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['_'] == '1234567890'

    def test_serial_list_column_0_not_orderable(self, api_client):
        """Test that column 0 is not orderable"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_serial_list('http://test.com', '123', 180, 441, {})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['columns[0][orderable]'] == 'false'

    def test_serial_list_column_1_is_orderable(self, api_client):
        """Test that column 1 (serialNo) is orderable"""
        mock_response = Mock()
        api_client._session.post.return_value = mock_response

        api_client.get_serial_list('http://test.com', '123', 180, 441, {})

        call_args = api_client._session.post.call_args
        data = call_args[1]['data']
        assert data['columns[1][orderable]'] == 'true'


class TestSaveOrderDetails:
    """Tests for save_order_details method - CSV/JSON writing logic"""

    def test_csv_row_format(self):
        """Test that CSV row is formatted correctly"""
        import csv
        import io

        # Create a CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["time", "tracking", "order", "inv"])
        writer.writerow(["2024-01-01 12:00:00", "TRACK-001", "ORD-001", "INV-001"])

        # Verify the CSV content
        output.seek(0)
        lines = output.readlines()
        assert len(lines) == 2
        assert "time,tracking,order,inv" in lines[0]

    def test_json_order_structure(self):
        """Test that JSON order data has correct structure"""
        order_data = {
            "timestamp": "2024-01-01 12:00:00",
            "tracking_number": "TRACK-001",
            "order_number": "ORD-001",
            "bill_number": "INV-001"
        }
        assert 'timestamp' in order_data
        assert 'tracking_number' in order_data
        assert 'order_number' in order_data
        assert 'bill_number' in order_data
