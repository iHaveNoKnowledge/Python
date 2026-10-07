import time
from typing import Optional, Tuple
import keyring


class AccountManager:
    """
    Manages user credentials and persistent 1-hour local sessions.
    Stores last username and time-limited session (user_id, password, timestamp) via keyring.
    """

    def __init__(self, service_name: str = "AutoSamaticMKII"):
        self.service_name = service_name

    def set_last_username(self, username: str) -> None:
        try:
            if username:
                keyring.set_password(self.service_name, "last_user", username)
        except Exception as e:
            print(f"Error setting last_username in keyring: {e}")

    def get_last_username(self) -> Optional[str]:
        try:
            return keyring.get_password(self.service_name, "last_user")
        except Exception as e:
            print(f"Error getting last_username from keyring: {e}")
            return None

    def save_session(
        self,
        user_id: str,
        password: str,
        accel_file_dir: Optional[str] = None,
        cp_table_location: Optional[str] = None,
    ) -> None:
        """
        Saves user credentials with current epoch timestamp to create a session.
        Optionally persists selected accel_file_dir and cp_table_location.
        """
        try:
            now_ts = str(time.time())
            keyring.set_password(self.service_name, "session_user", user_id)
            keyring.set_password(self.service_name, "session_pass", password)
            keyring.set_password(self.service_name, "session_time", now_ts)
            self.set_last_username(user_id)
            if accel_file_dir is not None:
                keyring.set_password(self.service_name, "session_accel_dir", accel_file_dir)
            if cp_table_location is not None:
                keyring.set_password(self.service_name, "session_cp_path", cp_table_location)
        except Exception as e:
            print(f"Error saving session to keyring: {e}")

    def save_session_paths(
        self,
        accel_file_dir: Optional[str] = None,
        cp_table_location: Optional[str] = None,
    ) -> None:
        """
        Updates stored paths in session without changing credentials or reset timestamp.
        """
        try:
            if accel_file_dir is not None:
                keyring.set_password(self.service_name, "session_accel_dir", accel_file_dir)
            if cp_table_location is not None:
                keyring.set_password(self.service_name, "session_cp_path", cp_table_location)
        except Exception as e:
            print(f"Error saving session paths to keyring: {e}")

    def touch_session(self) -> None:
        """
        Updates session timestamp to the current epoch time.
        Called on exit, periodically, or on active usage so that the 1-hour expiration countdown
        only starts from the moment of last activity / bot close.
        """
        try:
            session_user = keyring.get_password(self.service_name, "session_user")
            session_pass = keyring.get_password(self.service_name, "session_pass")
            if session_user and session_pass:
                keyring.set_password(self.service_name, "session_time", str(time.time()))
        except Exception as e:
            print(f"Error touching session timestamp in keyring: {e}")

    def get_active_session(self, max_age_seconds: int = 3600) -> Optional[Tuple[str, str]]:
        """
        Retrieves active (user_id, password) session if not expired (within max_age_seconds, default 1 hour).
        If expired, automatically clears the session and returns None.
        """
        try:
            session_user = keyring.get_password(self.service_name, "session_user")
            session_pass = keyring.get_password(self.service_name, "session_pass")
            session_time_str = keyring.get_password(self.service_name, "session_time")

            if not session_user or not session_pass or not session_time_str:
                return None

            session_time = float(session_time_str)
            elapsed = time.time() - session_time

            if 0 <= elapsed <= max_age_seconds:
                return (session_user, session_pass)
            else:
                # Session expired (> 1 hour)
                print(f"Session expired ({elapsed:.1f}s > {max_age_seconds}s). Clearing session...")
                self.clear_session()
                return None
        except Exception as e:
            print(f"Error retrieving active session from keyring: {e}")
            return None

    def get_session_data(self, max_age_seconds: int = 3600) -> Optional[dict]:
        """
        Retrieves complete active session dictionary including credentials and persisted paths.
        Returns dict: {'user_id': str, 'password': str, 'accel_file_dir': Optional[str], 'cp_table_location': Optional[str]}
        or None if expired / absent.
        """
        try:
            active = self.get_active_session(max_age_seconds=max_age_seconds)
            if not active:
                return None

            user_id, password = active
            accel_dir = keyring.get_password(self.service_name, "session_accel_dir")
            cp_path = keyring.get_password(self.service_name, "session_cp_path")

            return {
                "user_id": user_id,
                "password": password,
                "accel_file_dir": accel_dir if (accel_dir and accel_dir != "None") else None,
                "cp_table_location": cp_path if (cp_path and cp_path != "None") else None,
            }
        except Exception as e:
            print(f"Error retrieving session data from keyring: {e}")
            return None

    def clear_session(self) -> None:
        """
        Clears all stored session credentials, timestamp, and persisted paths (Logout).
        """
        for key in ["session_user", "session_pass", "session_time", "session_accel_dir", "session_cp_path"]:
            try:
                keyring.delete_password(self.service_name, key)
            except Exception:
                pass

    def is_session_valid(self, max_age_seconds: int = 3600) -> bool:
        return self.get_active_session(max_age_seconds=max_age_seconds) is not None

