"""Offline contract tests for Apollo loader; does not assert live Apollo integration."""
import hashlib
import json
import sys
import types
import unittest
from pathlib import Path

# GCS client is injected in these tests, so no Google SDK is needed.
google = types.ModuleType("google")
cloud = types.ModuleType("google.cloud")
cloud.storage = types.ModuleType("google.cloud.storage")
google.cloud = cloud
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.cloud", cloud)
sys.modules.setdefault("google.cloud.storage", cloud.storage)
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
        self.artifact = json.dumps({"product_id":"calculator","version":"1","ai_brain":"reason about math","ui_spec":"dynamic"}).encode()
        self.catalog = {"authority":"apollo","schema_version":"1.0","products":[{"product_id":"calculator","display_name":"Calculator","version":"1","approved":True,"activation_enabled":True,"artifact_object":"cartridges/c.json","artifact_sha256":hashlib.sha256(self.artifact).hexdigest()}]}
        self.objects = {"registry/products.v1.json":json.dumps(self.catalog).encode(),"cartridges/c.json":self.artifact}
        self.registry = ApolloRegistry("apollo-test",client=Client(self.objects))
    def test_list_and_exact_load(self):
        self.assertEqual(self.registry.list_products()[0].display_name,"Calculator")
        self.assertEqual(self.registry.get_product_artifact("calculator","1")["ai_brain"],"reason about math")
    def test_unapproved_fails_closed(self):
        self.catalog["products"][0]["approved"]=False
        self.objects["registry/products.v1.json"]=json.dumps(self.catalog).encode()
        self.assertEqual(self.registry.list_products(),[])
        with self.assertRaises(ApolloRegistryError): self.registry.get_product_artifact("calculator","1")
    def test_corrupt_artifact_fails(self):
        self.objects["cartridges/c.json"]=b"corrupt"
        with self.assertRaisesRegex(ApolloRegistryError,"CHECKSUM"): self.registry.get_product_artifact("calculator","1")
    def test_version_fails(self):
        with self.assertRaises(ApolloRegistryError): self.registry.get_product_artifact("calculator","2")

if __name__ == "__main__": unittest.main()
