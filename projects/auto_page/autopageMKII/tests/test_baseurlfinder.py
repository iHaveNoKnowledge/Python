# tests/test_baseurlfinder.py
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from requests.exceptions import ConnectionError, Timeout, RequestException

APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))
try:
    from functions.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder
except ImportError:
    from projects.auto_page.autopageMKII.functions.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder


@pytest.fixture
def sample_ips():
    return {
        "ip1": "http://115.31.167.28:8080",
        "ip2": "http://192.168.0.11:8080"
    }


@pytest.fixture
def mock_json_file(sample_ips):
    """Mock JSON file content"""
    import json
    return json.dumps(sample_ips)


class TestBaseUrlFinder:
    """Test suite for BaseUrlFinder class"""

    # ===== Test Initialization =====
    def test_init_with_valid_json(self, mock_json_file):
        """Test initialization with valid JSON file"""
        with patch("builtins.open", mock_open(read_data=mock_json_file)):
            finder = BaseUrlFinder("./json/urls.json")
            assert finder.ips_json == {
                "ip1": "http://115.31.167.28:8080",
                "ip2": "http://192.168.0.11:8080"
            }

    def test_init_with_missing_file(self, capsys):
        """Test initialization when JSON file is missing"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            finder = BaseUrlFinder("./nonexistent.json")
            assert finder.ips_json == {}
            captured = capsys.readouterr()
            assert "was not found" in captured.out

    def test_init_with_invalid_json(self, capsys):
        """Test initialization with invalid JSON content"""
        with patch("builtins.open", mock_open(read_data="invalid json{")):
            finder = BaseUrlFinder("./json/urls.json")
            assert finder.ips_json == {}
            captured = capsys.readouterr()
            assert "Failed to decode JSON" in captured.out

    # ===== Test check_available_ip =====
    @patch("functions.BaseUrlFinder.BaseUrlFinder.requests.get")
    def test_check_available_ip_first_success(self, mock_get, sample_ips):
        """Test when first IP returns 200"""
        finder = BaseUrlFinder()
        finder.ips_json = sample_ips

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = finder.check_available_ip()
        assert result == "http://115.31.167.28:8080"
        mock_get.assert_called_once_with("http://115.31.167.28:8080", timeout=2)

    @patch("functions.BaseUrlFinder.BaseUrlFinder.requests.get")
    def test_check_available_ip_second_success(self, mock_get, sample_ips):
        """Test when first IP fails, second succeeds"""
        finder = BaseUrlFinder()
        finder.ips_json = sample_ips

        def side_effect(url, timeout):
            if url == "http://115.31.167.28:8080":
                raise ConnectionError("Connection failed")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            return mock_resp

        mock_get.side_effect = side_effect
        result = finder.check_available_ip()
        assert result == "http://192.168.0.11:8080"
        assert mock_get.call_count == 2

    @patch("functions.BaseUrlFinder.BaseUrlFinder.requests.get")
    def test_check_available_ip_non_200_status(self, mock_get, sample_ips):
        """Test when IP returns non-200 status code"""
        finder = BaseUrlFinder()
        finder.ips_json = sample_ips

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = finder.check_available_ip()
        assert result is None

    @patch("functions.BaseUrlFinder.BaseUrlFinder.requests.get")
    def test_check_available_ip_connection_error(self, mock_get, sample_ips):
        """Test when ConnectionError is raised"""
        finder = BaseUrlFinder()
        finder.ips_json = sample_ips

        mock_get.side_effect = ConnectionError("Connection refused")
        result = finder.check_available_ip()
        assert result is None

    @patch("functions.BaseUrlFinder.BaseUrlFinder.requests.get")
    def test_check_available_ip_timeout(self, mock_get, sample_ips):
        """Test when Timeout is raised"""
        finder = BaseUrlFinder()
        finder.ips_json = sample_ips

        mock_get.side_effect = Timeout("Request timed out")
        result = finder.check_available_ip()
        assert result is None

    @patch("functions.BaseUrlFinder.BaseUrlFinder.requests.get")
    def test_check_available_ip_request_exception(self, mock_get, sample_ips):
        """Test when general RequestException is raised"""
        finder = BaseUrlFinder()
        finder.ips_json = sample_ips

        mock_get.side_effect = RequestException("Unexpected error")
        result = finder.check_available_ip()
        assert result is None

    def test_check_available_ip_empty_json(self):
        """Test when ips_json is empty"""
        finder = BaseUrlFinder()
        finder.ips_json = {}

        result = finder.check_available_ip()
        assert result is None

    def test_check_available_ip_none_json(self):
        """Test when ips_json is None"""
        finder = BaseUrlFinder()
        finder.ips_json = None

        result = finder.check_available_ip()
        assert result is None


# ===== Integration Test =====
@pytest.mark.integration
def test_real_connection():
    """Integration test with real HTTP request (optional)"""
    finder = BaseUrlFinder()
    finder.ips_json = {"test": "https://www.google.com"}
    
    result = finder.check_available_ip()
    assert result == "https://www.google.com"