"""No network calls: contract tests using an injected fake Gemini client."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from gemini_adapter import make_gemini_reasoner, GeminiAdapterError


class FakeModels:
    def __init__(self, response):
        self.response = response
        self.kwargs = None
    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"text": self.response})()


class FakeClient:
    def __init__(self, response):
        self.models = FakeModels(response)


class GeminiAdapterTests(unittest.TestCase):
    def test_preview_contract(self):
        client = FakeClient('{"status":"preview","ui_parts":[{"type":"text","content":"Hello"}]}')
        reason = make_gemini_reasoner(model="gemini-3.5-flash-lite", client=client)
        result = reason(product_id="calculator", user_message="Hello",
                        context=[{"document_id":"d1","content":"test"}], instruction="safe")
        self.assertEqual(result["status"], "preview")
        self.assertEqual(client.models.kwargs["model"], "gemini-3.5-flash-lite")
        self.assertEqual(client.models.kwargs["config"]["response_mime_type"], "application/json")

    def test_followup_contract(self):
        client = FakeClient('{"status":"needs_more_context","search_query":"more details"}')
        result = make_gemini_reasoner(model="gemini-3.5-flash-lite", client=client)(
            product_id="calculator", user_message="x",
            context=[{"document_id":"d1","content":"test"}], instruction="safe")
        self.assertEqual(result["search_query"], "more details")

    def test_deprecated_model_blocked(self):
        with self.assertRaisesRegex(GeminiAdapterError, "LIFECYCLE_STOP"):
            make_gemini_reasoner(model="gemini-2.5-flash", client=FakeClient("{}"))

    def test_model_required(self):
        with patch.dict(os.environ, {"MORPHEUS_GEMINI_MODEL": ""}):
            with self.assertRaisesRegex(GeminiAdapterError, "MODEL_REQUIRED"):
                make_gemini_reasoner(client=FakeClient("{}"))

    def test_invalid_json_stops(self):
        client = FakeClient("not JSON")
        with self.assertRaisesRegex(GeminiAdapterError, "INVALID_RESPONSE"):
            make_gemini_reasoner(model="gemini-3.5-flash-lite", client=client)(
                product_id="calculator", user_message="x",
                context=[{"document_id":"d1","content":"test"}], instruction="safe")

    def test_missing_evidence_stops(self):
        with self.assertRaisesRegex(GeminiAdapterError, "CONTEXT_REQUIRED"):
            make_gemini_reasoner(model="gemini-3.5-flash-lite", client=FakeClient("{}"))(
                product_id="calculator", user_message="x", context=[], instruction="safe")


if __name__ == "__main__":
    unittest.main()
