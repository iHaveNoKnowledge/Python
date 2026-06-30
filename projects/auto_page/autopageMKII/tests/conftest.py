import pytest
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Environment URLs
UAT_URL = "http://192.168.0.142:9099/smartcore/smartpos"
PROD_URL = "http://192.168.0.11:8080/smartcore/smartpos"

# Test data file path
TEST_DATA_FILE = r"C:\Users\Satawad_Ta\Downloads\Order.toship.20260623_20260630.xlsx"


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="prod",
        help="Environment to run tests: uat or prod"
    )
    parser.addoption(
        "--allow-receipt",
        action="store_true",
        default=False,
        help="Allow receipt issuance (only for UAT)"
    )


@pytest.fixture(scope="session")
def driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # Selenium 4.6+ uses Selenium Manager to auto-download correct ChromeDriver
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


@pytest.fixture
def environment(request):
    return request.config.getoption("--env")


@pytest.fixture
def smco_url(environment):
    if environment == "uat":
        return UAT_URL
    return PROD_URL


@pytest.fixture
def allow_receipt(request):
    return request.config.getoption("--allow-receipt")


@pytest.fixture
def require_uat(environment):
    if environment != "uat":
        pytest.skip("Test requires UAT environment")


@pytest.fixture
def prevent_receipt(allow_receipt, environment):
    if environment == "prod" and not allow_receipt:
        pytest.skip("Receipt issuance not allowed in Production")


@pytest.fixture(scope="session")
def test_data():
    """Load test data from Excel file"""
    df = pd.read_excel(TEST_DATA_FILE, dtype=str)
    return df


@pytest.fixture
def sample_order(test_data):
    """Get a sample order from test data"""
    if test_data.empty:
        pytest.skip("No test data available")
    return test_data.iloc[0]


@pytest.fixture
def sample_orders(test_data, limit=5):
    """Get multiple sample orders from test data"""
    if test_data.empty:
        pytest.skip("No test data available")
    return test_data.head(limit)


@pytest.fixture
def orders_by_status(test_data):
    """Get orders grouped by status"""
    if test_data.empty:
        pytest.skip("No test data available")
    return {
        'pending': test_data[test_data['สถานะการสั่งซื้อ'] == 'pending'],
        'completed': test_data[test_data['สถานะการสั่งซื้อ'] == 'completed'],
        'cancelled': test_data[test_data['สถานะการสั่งซื้อ'] == 'cancelled']
    }
