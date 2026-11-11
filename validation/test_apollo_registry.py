"""Offline contract tests for Apollo registry. Uses fake GCS, not live Apollo."""
import hashlib
import json
import sys
import types
import unittest
from pathlib import Path

try:
    from google.cloud import storage
except ImportError:
    google = sys.modules.setdefault("google", types.ModuleType("google"))
    cloud = sys.modules.setdefault("google.cloud", types.ModuleType("google.cloud"))
    cloud.storage = sys.modules.setdefault("google.cloud.storage", types.ModuleType("google.cloud.storage"))
    google.cloud = cloud
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from apollo_registry import ApolloRegistry, ApolloRegistryError

class Blob:
    def __init__(self, value): self.value = value
    def download_as_bytes(self): return self.value

class Bucket:
    def __init__(self, objects): self.objects = objects
    def blob(self, key): return Blob(self.objects[key])

class Client:
    def __init__(self, objects): self.objects = objects
    def bucket(self, name): return Bucket(self.objects)

class Tests(unittest.TestCase):
    def setUp(self):
        self.artifact = {"product_id": "calculator", "version": "1.0.0", "ai_brain": "math intent",
                         "ui_spec": {"type": "text"}, "agents": [{"id": "math-agent"}],
                         "permissions": {}, "behavioral_contract": "validated math",
                         "compatible_platform": "morpheus_adaptive_ui"}
        self.catalog = {"authority": "apollo", "schema_version": "1.0", "products": [
            {"product_id": "calculator", "display_name": "Calculator", "version": "1.0.0",
             "approved": True, "activation_enabled": True, "artifact_object": "cartridges/c.json",
             "artifact_sha256": ""}]}
        self.objects = {}
        self.sync()
        self.registry = ApolloRegistry("apollo-test", client=Client(self.objects))

    def sync(self):
        raw = json.dumps(self.artifact).encode()
        self.catalog["products"][0]["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        self.objects["cartridges/c.json"] = raw
        self.objects["registry/products.v1.json"] = json.dumps(self.catalog).encode()

    def test_exact_load(self):
        self.assertEqual(self.registry.get_product_artifact("calculator", "1.0.0")["agents"][0]["id"], "math-agent")

    def test_unapproved_stop(self):
        self.catalog["products"][0]["approved"] = False; self.sync()
        self.assertEqual(self.registry.list_products(), [])
        with self.assertRaisesRegex(ApolloRegistryError, "UNKNOWN_OR_UNAPPROVED"):
            self.registry.get_product_artifact("calculator", "1.0.0")

    def test_disabled_stop(self):
        self.catalog["products"][0]["activation_enabled"] = False; self.sync()
        self.assertEqual(self.registry.list_products(), [])

    def test_checksum_stop(self):
        self.objects["cartridges/c.json"] = b"tampered"
        with self.assertRaisesRegex(ApolloRegistryError, "CHECKSUM"):
            self.registry.get_product_artifact("calculator", "1.0.0")

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
        self.sync(); self.catalog["products"][0]["artifact_sha256"] = "z" * 64
        self.objects["registry/products.v1.json"] = json.dumps(self.catalog).encode()
        with self.assertRaisesRegex(ApolloRegistryError, "INVALID_PRODUCT_ENTRY"):
            self.registry.list_products()

    def test_bad_path_stop(self):
        with self.assertRaisesRegex(ApolloRegistryError, "INVALID_OBJECT_PATH"):
            self.registry._read("../secrets")

if __name__ == "__main__":
    unittest.main()
