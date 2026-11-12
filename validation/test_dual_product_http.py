"""End-to-end Flask route tests for both real product engines with an injected catalog.

These are in-process functional integration tests, not a claim of live Apollo or BAT.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api

class CandidateCatalog:
    def list_candidates(self):
        return [{"product_id":"calculator","display_name":"Calculator","version":"1.0.0",
                 "approved":False,"activation_enabled":False},
                {"product_id":"hippocrates_labs","display_name":"Hippocrates Labs","version":"1.0.0",
                 "approved":False,"activation_enabled":False}]

class ProductRoutes(unittest.TestCase):
    def setUp(self):
        self.patcher = patch.object(api, "configured_apollo_registry", return_value=CandidateCatalog())
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.client = api.create_app().test_client()
    def test_candidate_discovery_is_not_activation(self):
        response = self.client.get("/api/candidates")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(len(body["products"]), 2)
        self.assertFalse(body["production_activation"])
        self.assertFalse(any(x["activation_enabled"] for x in body["products"]))
    def test_calculator_http_functional_result(self):
        response = self.client.post("/api/execute", json={"product_id":"calculator","expression":"(12+8)/4"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["result"]["result"], 5)
        self.assertFalse(response.get_json()["production_activation"])
    def test_labs_http_functional_result(self):
        response = self.client.post("/api/execute", json={"product_id":"hippocrates_labs",
            "measurements":[{"name":"WBC","value":12,"unit":"10^3/uL","low":4,"high":11}]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["result"]["measurements"][0][-1], "above supplied range")
    def test_unknown_product_rejected(self):
        response = self.client.post("/api/execute", json={"product_id":"unlisted","expression":"2+2"})
        self.assertEqual(response.status_code, 422)
    def test_invalid_calculation_rejected(self):
        response = self.client.post("/api/execute", json={"product_id":"calculator","expression":"1/0"})
        self.assertEqual(response.status_code, 422)
    def test_preview_simulation_not_used_in_apollo_mode(self):
        response = self.client.post("/api/preview", json={"product_id":"calculator","message":"2+2"})
        self.assertEqual(response.status_code, 409)

if __name__ == "__main__":
    unittest.main()
