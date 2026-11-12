"""Offline contract tests for Morpheus's authenticated Apollo API adapter."""
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from apollo_registry import ApolloRegistry, ApolloRegistryError


def encoded(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class Response:
    status = 200
    def __init__(self, payload):
        self.body = io.BytesIO(json.dumps(payload).encode("utf-8"))
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.body.close()
    def read(self, n=-1):
        return self.body.read(n)


class FakeApollo:
    def __init__(self, owner):
        self.owner = owner
        self.calls = []
        self.failure = None

    def __call__(self, request, timeout):
        self.calls.append((request.full_url, request.get_header("X-apollo-write-key"), timeout))
        if self.failure:
            raise self.failure
        path = request.full_url.split("/products/", 1)[1]
        product_id, suffix = path.split("/documents/", 1)
        document_id = suffix.removesuffix("/content")
        if document_id == "catalog":
            content = self.owner.catalog_raw
            sha = digest(content)
        elif document_id == "cartridge":
            content = self.owner.artifact_raw
            sha = digest(content)
        else:
            raise HTTPError(request.full_url, 404, "not found", {}, None)
        return Response({"decision": "PASS", "product_id": product_id,
                         "document_id": document_id, "document_type": "json",
                         "sha256": sha, "content": content})


class Tests(unittest.TestCase):
    def setUp(self):
        self.artifact = {"product_id": "calculator", "version": "1.0.0",
                         "ai_brain": "math intent", "ui_spec": {"type": "text"},
                         "agents": [{"id": "math-agent"}], "permissions": {},
                         "behavioral_contract": "validated math",
                         "compatible_platform": "morpheus_adaptive_ui"}
        self.catalog = {"authority": "apollo", "schema_version": "1.0",
                        "products": [{"product_id": "calculator",
                                      "display_name": "Calculator", "version": "1.0.0",
                                      "approved": True, "activation_enabled": True,
                                      "artifact_document_id": "cartridge",
                                      "artifact_sha256": ""}]}
        self.fake = FakeApollo(self)
        self.sync()

    def sync(self):
        self.artifact_raw = encoded(self.artifact)
        self.catalog["products"][0]["artifact_sha256"] = digest(self.artifact_raw)
        self.catalog_raw = encoded(self.catalog)
        self.registry = ApolloRegistry("https://apollo.example", "fake-test-key",
                                       catalog_document_id="catalog",
                                       catalog_sha256=digest(self.catalog_raw),
                                       opener=self.fake)

    def test_exact_load(self):
        self.assertEqual(self.registry.get_product_artifact("calculator", "1.0.0")["agents"][0]["id"], "math-agent")
        self.assertEqual(len(self.fake.calls), 2)
        self.assertTrue(all(call[1] == "fake-test-key" for call in self.fake.calls))

    def test_unapproved_stop(self):
        self.catalog["products"][0]["approved"] = False; self.sync()
        self.assertEqual(self.registry.list_products(), [])
        with self.assertRaisesRegex(ApolloRegistryError, "UNKNOWN_OR_UNAPPROVED"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_disabled_stop(self):
        self.catalog["products"][0]["activation_enabled"] = False; self.sync()
        self.assertEqual(self.registry.list_products(), [])

    def test_checksum_stop(self):
        self.artifact_raw = "tampered"
        with self.assertRaisesRegex(ApolloRegistryError, "CHECKSUM"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_catalog_checksum_stop(self):
        self.catalog_raw = "tampered"
        with self.assertRaisesRegex(ApolloRegistryError, "CHECKSUM"):
            self.registry.list_products()

    def test_version_stop(self):
        with self.assertRaisesRegex(ApolloRegistryError, "UNKNOWN_OR_UNAPPROVED"):
            self.registry.get_product_artifact("calculator", "2.0.0")

    def test_identity_stop(self):
        self.artifact["product_id"] = "hippocrates_labs"; self.sync()
        with self.assertRaisesRegex(ApolloRegistryError, "IDENTITY"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_missing_brain_stop(self):
        del self.artifact["ai_brain"]; self.sync()
        with self.assertRaisesRegex(ApolloRegistryError, "INCOMPLETE"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_invalid_agents_stop(self):
        self.artifact["agents"] = [{"role": "missing id"}]; self.sync()
        with self.assertRaisesRegex(ApolloRegistryError, "AGENT_CONTRACT"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_invalid_permissions_stop(self):
        self.artifact["permissions"] = ["unsafe"]; self.sync()
        with self.assertRaisesRegex(ApolloRegistryError, "PERMISSIONS"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_wrong_platform_stop(self):
        self.artifact["compatible_platform"] = "other"; self.sync()
        with self.assertRaisesRegex(ApolloRegistryError, "INCOMPATIBLE_PLATFORM"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_duplicate_version_stop(self):
        self.catalog["products"].append(dict(self.catalog["products"][0])); self.sync()
        with self.assertRaisesRegex(ApolloRegistryError, "DUPLICATE"):
            self.registry.list_products()

    def test_bad_catalog_stop(self):
        self.catalog["authority"] = "untrusted"; self.sync()
        with self.assertRaisesRegex(ApolloRegistryError, "INVALID_APOLLO_CATALOG"):
            self.registry.list_products()

    def test_bad_hash_format_stop(self):
        self.sync()
        self.catalog["products"][0]["artifact_sha256"] = "z" * 64
        self.catalog_raw = encoded(self.catalog)
        self.registry.catalog_sha256 = digest(self.catalog_raw)
        with self.assertRaisesRegex(ApolloRegistryError, "INVALID_ARTIFACT_DIGEST"):
            self.registry.list_products()

    def test_bad_identity_stop(self):
        with self.assertRaisesRegex(ApolloRegistryError, "INVALID_DOCUMENT_IDENTITY"):
            self.registry._exact_document("../secrets", "cartridge", "0" * 64)

    def test_missing_catalog_stop(self):
        registry = ApolloRegistry("https://apollo.example", "fake-test-key", opener=self.fake)
        with self.assertRaisesRegex(ApolloRegistryError, "NOT_CONFIGURED"):
            registry.list_products()

    def test_insecure_url_stop(self):
        with self.assertRaisesRegex(ApolloRegistryError, "INVALID_APOLLO_URL"):
            ApolloRegistry("http://apollo.example", "fake-test-key")

    def test_http_failure_stop(self):
        self.fake.failure = HTTPError("https://apollo.example", 403, "denied", {}, None)
        with self.assertRaisesRegex(ApolloRegistryError, "APOLLO_READ_FAILED"):
            self.registry.list_products()


if __name__ == "__main__":
    unittest.main()
