"""Negative and identity tests for development-only Apollo evaluation gate."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from development_cartridges import get_development_cartridge, CANDIDATES
from apollo_registry import ApolloRegistryError

class Registry:
    def __init__(self, artifact):
        self.artifact = artifact
        self.calls = []
    def _exact_document(self, pid, doc, sha):
        self.calls.append((pid, doc, sha))
        return self.artifact

class GateTests(unittest.TestCase):
    def setUp(self):
        self.pid = "calculator"
        self.pin = CANDIDATES[self.pid][1]
        self.env = {"MORPHEUS_ENV":"development",
                    "MORPHEUS_DEV_CARTRIDGES_ENABLED":"true",
                    "MORPHEUS_DEV_CALCULATOR_SHA256":self.pin}
        self.artifact = {
            "schema_version":"1.0","product_id":"calculator","version":"1.0.0",
            "compatible_platform":"morpheus_adaptive_ui",
            "approval_status":"PENDING_VALIDATION",
            "ai_brain":{"role":"Arithmetic","constraints":["No arbitrary code"]},
            "behavioral_contract":{"source_document_ids":["source"],"requirements":["Safe arithmetic"]},
            "permissions":{"allowed_actions":["calculator:compute"],"external_data":False},
            "ui_spec":{"allowed_components":["text","input","action","table"],
                       "fields":[{"id":"expression","type":"text","label":"Expression",
                                  "required":True,"max_length":200}],
                       "action":{"id":"calculate","adapter":"calculator",
                                 "payload_binding":{"expression":"expression"}},
                       "result_components":["text"]}
        }
        self.registry = Registry(self.artifact)

    def test_pinned_candidate_passes_without_approval(self):
        result=get_development_cartridge(self.registry,self.pid,"1.0.0",environ=self.env)
        self.assertEqual(result["approval_status"],"PENDING_VALIDATION")
        self.assertEqual(self.registry.calls,[("calculator",*CANDIDATES["calculator"])])

    def test_disabled_stops_before_read(self):
        self.env["MORPHEUS_DEV_CARTRIDGES_ENABLED"]="false"
        with self.assertRaisesRegex(ApolloRegistryError,"DISABLED"):
            get_development_cartridge(self.registry,self.pid,"1.0.0",environ=self.env)
        self.assertEqual(self.registry.calls,[])

    def test_production_stops_before_read(self):
        self.env["MORPHEUS_ENV"]="production"
        with self.assertRaisesRegex(ApolloRegistryError,"ENV_STOP"):
            get_development_cartridge(self.registry,self.pid,"1.0.0",environ=self.env)
        self.assertEqual(self.registry.calls,[])

    def test_wrong_pin_stops_before_read(self):
        self.env["MORPHEUS_DEV_CALCULATOR_SHA256"]="0"*64
        with self.assertRaisesRegex(ApolloRegistryError,"PIN_STOP"):
            get_development_cartridge(self.registry,self.pid,"1.0.0",environ=self.env)
        self.assertEqual(self.registry.calls,[])

    def test_wrong_product_stops(self):
        with self.assertRaisesRegex(ApolloRegistryError,"UNKNOWN"):
            get_development_cartridge(self.registry,"unlisted","1.0.0",environ=self.env)

    def test_approved_status_not_a_candidate(self):
        self.artifact["approval_status"]="APPROVED"
        with self.assertRaisesRegex(ApolloRegistryError,"STATUS_STOP"):
            get_development_cartridge(self.registry,self.pid,"1.0.0",environ=self.env)

if __name__ == "__main__":
    unittest.main()
