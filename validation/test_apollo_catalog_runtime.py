"""Contract tests for Apollo catalog runtime selection (no external network)."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import create_app, configured_apollo_registry
from apollo_registry import ApolloRegistryError

class CatalogRuntimeTests(unittest.TestCase):
    def test_catalog_configuration_is_pinned(self):
        with patch.dict(os.environ, {"MORPHEUS_REGISTRY_MODE": "apollo", "APOLLO_WRITE_KEY": "test-only"}, clear=False):
            registry = configured_apollo_registry()
            self.assertEqual(registry.catalog_document_id, "177030db19704abaa93059dcf10c7172")
            self.assertEqual(registry.catalog_sha256, "f9e600689c48ae459ceb7fc4bcdf67d3089f55ab5ae5340a91ac229fe3b8f1b7")

    def test_missing_credentials_stop(self):
        with patch.dict(os.environ, {"MORPHEUS_REGISTRY_MODE": "apollo", "APOLLO_WRITE_KEY": ""}, clear=False):
            with self.assertRaisesRegex(ApolloRegistryError, "CREDENTIAL_MISSING"):
                configured_apollo_registry()

    def test_apollo_mode_does_not_enable_preview(self):
        with patch.dict(os.environ, {"MORPHEUS_REGISTRY_MODE": "apollo", "APOLLO_WRITE_KEY": "test-only"}, clear=False):
            app = create_app()
            response = app.test_client().post("/api/preview", json={"product_id":"calculator","message":"1+1"})
            self.assertEqual(response.status_code, 409)
            self.assertIn("DISABLED", response.get_json()["error"])

if __name__ == "__main__":
    unittest.main()
