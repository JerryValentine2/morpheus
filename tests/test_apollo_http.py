"""Offline tests for Apollo HTTP transport; no live service required."""
import io
import json
import unittest
from unittest.mock import patch
from runtime.apollo_http import ApolloAPIError, ApolloHTTPClient


class Response(io.BytesIO):
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class ApolloHTTPTests(unittest.TestCase):
    def test_https_required(self):
        with self.assertRaises(ApolloAPIError):
            ApolloHTTPClient("http://example.com", "key")

    def test_credentials_required(self):
        with self.assertRaises(ApolloAPIError):
            ApolloHTTPClient("https://example.com", "")

    def test_document_identity_validation(self):
        client = ApolloHTTPClient("https://example.com", "key")
        with self.assertRaises(ApolloAPIError):
            client.read_document_content("../other", "doc")

    def test_exact_read_request(self):
        client = ApolloHTTPClient("https://example.com", "key")
        payload = {"product_id": "morpheus_adaptive_ui", "content": "sample"}
        with patch("runtime.apollo_http.urllib.request.urlopen", return_value=Response(json.dumps(payload).encode())) as mocked:
            self.assertEqual(client.read_document_content("morpheus_adaptive_ui", "doc123"), payload)
            req = mocked.call_args.args[0]
            self.assertEqual(req.get_method(), "GET")
            self.assertEqual(req.get_header("X-api-key"), "key")
            self.assertTrue(req.full_url.endswith("/products/morpheus_adaptive_ui/documents/doc123/content"))

    def test_invalid_response(self):
        client = ApolloHTTPClient("https://example.com", "key")
        with patch("runtime.apollo_http.urllib.request.urlopen", return_value=Response(b"[]")):
            with self.assertRaises(ApolloAPIError):
                client.read_document_content("product", "doc")


if __name__ == "__main__":
    unittest.main()
