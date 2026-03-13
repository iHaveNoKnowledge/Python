import keyring


class AccountManager:
    def __init__(self, service_name):
        self.service_name = service_name

    def set_last_username(self, username):
        keyring.set_password(self.service_name, "last_user", username)

    def get_last_username(self):
        return keyring.get_password(self.service_name, "last_user")
