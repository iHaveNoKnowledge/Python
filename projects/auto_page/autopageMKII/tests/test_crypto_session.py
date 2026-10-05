import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.utils.crypto import AccountManager


class DummyKeyring:
    def __init__(self):
        self.store = {}

    def set_password(self, service, username, password):
        self.store[(service, username)] = password

    def get_password(self, service, username):
        return self.store.get((service, username))

    def delete_password(self, service, username):
        key = (service, username)
        if key in self.store:
            del self.store[key]


@pytest.fixture
def mock_keyring():
    dummy = DummyKeyring()
    with patch("functions.utils.crypto.keyring.set_password", side_effect=dummy.set_password), \
         patch("functions.utils.crypto.keyring.get_password", side_effect=dummy.get_password), \
         patch("functions.utils.crypto.keyring.delete_password", side_effect=dummy.delete_password):
        yield dummy


def test_save_and_get_active_session(mock_keyring):
    manager = AccountManager("TestService")
    manager.save_session("62078", "Secret123")

    session = manager.get_active_session(max_age_seconds=3600)
    assert session is not None
    user_id, password = session
    assert user_id == "62078"
    assert password == "Secret123"
    assert manager.is_session_valid(max_age_seconds=3600) is True


def test_session_expiration(mock_keyring):
    manager = AccountManager("TestService")
    manager.save_session("62078", "Secret123")

    # Fast forward time past 1 hour (3601 seconds)
    saved_time = float(mock_keyring.store[("TestService", "session_time")])
    with patch("time.time", return_value=saved_time + 3601):
        session = manager.get_active_session(max_age_seconds=3600)
        assert session is None
        assert manager.is_session_valid(max_age_seconds=3600) is False

    # Check that session was cleared from keyring
    assert ("TestService", "session_user") not in mock_keyring.store
    assert ("TestService", "session_pass") not in mock_keyring.store


def test_clear_session_logout(mock_keyring):
    manager = AccountManager("TestService")
    manager.save_session("62078", "Secret123")
    assert manager.get_active_session() is not None

    # Clear session (logout)
    manager.clear_session()
    assert manager.get_active_session() is None
    assert manager.is_session_valid() is False


def test_last_username_persists_after_logout(mock_keyring):
    manager = AccountManager("TestService")
    manager.save_session("62078", "Secret123")
    manager.clear_session()

    # last_username should still remain remembered even after session is logged out
    assert manager.get_last_username() == "62078"
