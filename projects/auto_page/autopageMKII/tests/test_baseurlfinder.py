# tests/test_baseurlfinder.py
import pytest
from unittest.mock import patch, MagicMock
from projects.auto_page.autopageMKII.modules.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder

print("BaseUrlFinder: ", BaseUrlFinder)


@pytest.fixture
def sample_ips():
    return {"ip1": "http://127.0.0.1", "ip2": "http://192.168.0.1"}


def test_check_available_ip_success(sample_ips):
    """Test when first IP is available (status 200)"""
    finder = BaseUrlFinder()
    finder.ips_json = sample_ips

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = finder.check_available_ip()
        assert result == "http://127.0.0.1"


def test_check_available_ip_second_ip_success(sample_ips):
    """Test when first IP fails, second IP succeeds"""
    finder = BaseUrlFinder()
    finder.ips_json = sample_ips

    def side_effect(url, timeout):
        if url == "http://127.0.0.1":
            raise Exception("Connection failed")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        return mock_resp

    with patch("requests.get", side_effect=side_effect):
        result = finder.check_available_ip()
        assert result == "http://192.168.0.1"


def test_check_available_ip_none(sample_ips):
    """Test when all IPs fail"""
    finder = BaseUrlFinder()
    finder.ips_json = sample_ips

    with patch("requests.get", side_effect=Exception("Connection failed")):
        result = finder.check_available_ip()
        assert result is None


def test_check_available_ip_empty_json():
    """Test when ips_json is empty"""
    finder = BaseUrlFinder()
    finder.ips_json = {}

    result = finder.check_available_ip()
    assert result is None
