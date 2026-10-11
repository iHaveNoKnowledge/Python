import unittest
import time
import tempfile
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from functions.pos.cp_data_loader import DualSourceCPLoader

class TestAsyncGASPush(unittest.TestCase):
    def setUp(self):
        self.gas_url = "https://script.google.com/macros/s/TEST/exec"
        self.loader = DualSourceCPLoader(gas_url=self.gas_url)

    def test_sync_push_blocks_and_returns_result(self):
        """is_async=False should block until requests.post finishes"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "success"}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            payload = {"sku": "TEST-SKU-1", "sale_price": 100.0}
            result = self.loader.push_record_to_gas(payload, is_async=False)
            self.assertTrue(result)
            mock_post.assert_called_once_with(self.gas_url, json=payload, timeout=8)

    def test_async_push_returns_immediately_without_blocking(self):
        """is_async=True should spawn background thread and return immediately"""
        def slow_post(*args, **kwargs):
            time.sleep(0.3)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "success"}
            return mock_resp

        with patch("requests.post", side_effect=slow_post) as mock_post:
            payload = {"sku": "TEST-SKU-ASYNC", "sale_price": 250.0}
            start_t = time.time()
            result = self.loader.push_record_to_gas(payload, is_async=True)
            elapsed = time.time() - start_t

            # push_record_to_gas must return virtually instantly (< 0.1s)
            self.assertTrue(result)
            self.assertLess(elapsed, 0.1, f"Expected non-blocking call, but took {elapsed:.4f}s")

            # Wait for background daemon thread to finish
            time.sleep(0.4)
            mock_post.assert_called_once()

    def test_duplicate_skips_without_calling_post(self):
        """If record is identical to cached dataframe, skip POST immediately"""
        cached_df = pd.DataFrame([{
            "sku": "DUP-SKU-1",
            "sale_price": 500.0,
            "cp_name": "CP1234",
            "last_order_id": "ORD001"
        }])
        self.loader._cached_df = cached_df

        with patch("requests.post") as mock_post:
            payload = {
                "sku": "DUP-SKU-1",
                "sale_price": 500.0,
                "cp_name": "CP1234",
                "last_order_id": "ORD001"
            }
            result = self.loader.push_record_to_gas(payload, is_async=True)
            self.assertTrue(result)
            mock_post.assert_not_called()

    def test_push_record_to_gas_async_convenience_method(self):
        """push_record_to_gas_async delegates with is_async=True"""
        with patch.object(self.loader, "push_record_to_gas", return_value=True) as mock_push:
            payload = {"sku": "CONVENIENCE-SKU", "sale_price": 1000.0}
            res = self.loader.push_record_to_gas_async(payload)
            self.assertTrue(res)
            mock_push.assert_called_once_with(payload, is_async=True)


if __name__ == "__main__":
    unittest.main()
