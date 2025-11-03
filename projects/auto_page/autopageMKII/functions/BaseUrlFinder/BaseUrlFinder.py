import requests
import json
from requests.exceptions import RequestException, ConnectionError, Timeout
import os


class BaseUrlFinder:
    """Finds an available base URL from a list of IPs."""

    def __init__(self, file_path: str = r".\json\misc.json"):
        # file_path =
        # self.base_dir = os.path.dirname(__file__)
        # self.file_path = os.path.join(self.base_dir, file_path)
        # self.ips_json = self._load_json_file(self.file_path)
        self.ips_json = json.loads(os.getenv("IPS"))
        print("self.ips_json: ", self.ips_json)

    # def _load_json_file(self, file_path: str):
    #     """Loads data from a JSON file."""
    #     try:
    #         with open(file_path, 'r', encoding='utf-8') as file:
    #             data = json.load(file)
    #         return data
    #     except FileNotFoundError:
    #         print(f"Error: The file '{file_path}' was not found.")
    #         return {}
    #     except json.JSONDecodeError:
    #         print(f"Error: Failed to decode JSON from '{file_path}'.")
    #         return {}

    def check_available_ip(self):
        """
        Checks a list of IPs for a successful connection.
        Returns the first available IP or None if none are found.
        """
        if not self.ips_json:
            print("No IPs to check. JSON file might be empty or invalid.")
            return None

        for ip in self.ips_json.values():
            try:
                response = requests.get(str(ip), timeout=2)
                if response.status_code == 200:
                    print(f"Found available IP: {ip} with status code 200")
                    return ip
                else:
                    print(f"Response code not 200 for IP: {ip}. Status code: {response.status_code}")
            except (ConnectionError, Timeout) as e:
                print(f"Could not connect to {ip}: {e}")
            except RequestException as e:
                print(f"An unexpected error occurred for {ip}: {e}")

        print("No available IP found after checking all options.")
        return None
