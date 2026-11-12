"""Contract tests for real AI planning route; no live model calls in CI."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api
from apollo_registry import ApolloRegistryError

class Registry:
    approved = True
    def get_product_artifact(self, product_id, version):
        if not self.approved:
            raise ApolloRegistryError("UNKNOWN_OR_UNAPPROVED_PRODUCT_VERSION")
        return {"product_id": product_id, "version": version,
                "ai_brain": {"role": "bounded assistant"},
                "ui_spec": {"allowed": ["text"]}}

class AdaptivePlanRoutes(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
        self.registry_patch = patch.object(api, "configured_apollo_registry", return_value=self.registry)
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)
        self.client = api.create_app().test_client()
        self.payload = {"product_id": "calculator", "version": "1.0.0", "message": "show a calculation"}

    def test_unapproved_artifact_stops_before_ai(self):
        self.registry.approved = False
        with patch.object(api, "make_gemini_reasoner") as ai:
            r = self.client.post("/api/adaptive-plan", json=self.payload)
        self.assertEqual(r.status_code, 409)
        ai.assert_not_called()

    def test_live_adapter_result_is_validated_and_not_executable(self):
        def reasoner(**kwargs):
            self.assertEqual(kwargs["product_id"], "calculator")
            self.assertTrue(kwargs["context"][0]["content"])
            return {"status": "preview", "ui_parts": [{"type": "text", "content": "Ready"}],
                    "source_document_ids": ["untrusted_model_claim"]}
        with patch.object(api, "make_gemini_reasoner", return_value=reasoner):
            r = self.client.post("/api/adaptive-plan", json=self.payload)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["ui_parts"], [{"type": "text", "content": "Ready"}])
        self.assertFalse(r.get_json()["executable"])
        self.assertNotIn("source_document_ids", r.get_json())

    def test_invalid_model_ui_stops(self):
        with patch.object(api, "make_gemini_reasoner", return_value=lambda **_: {
            "status": "preview", "ui_parts": [{"type": "script", "content": "alert(1)"}]}):
            r = self.client.post("/api/adaptive-plan", json=self.payload)
        self.assertEqual(r.status_code, 409)

    def test_model_stop_does_not_execute(self):
        with patch.object(api, "make_gemini_reasoner", return_value=lambda **_: {"status": "stop"}):
            r = self.client.post("/api/adaptive-plan", json=self.payload)
        self.assertEqual(r.status_code, 409)

    def test_invalid_request_stops_before_ai(self):
        with patch.object(api, "make_gemini_reasoner") as ai:
            r = self.client.post("/api/adaptive-plan", json={"product_id": "calculator"})
        self.assertEqual(r.status_code, 400)
        ai.assert_not_called()

if __name__ == "__main__":
    unittest.main()
