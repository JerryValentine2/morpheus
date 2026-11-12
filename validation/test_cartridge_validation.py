"""Deterministic contract validation for both Apollo cartridge candidate shapes."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from cartridge_validation import validate_cartridge, CartridgeValidationError

def candidate(pid):
    field = ({"id":"expression","label":"Calculation","type":"text","required":True,"max_length":200}
             if pid == "calculator" else
             {"id":"measurements","label":"Lab measurements","type":"measurement_rows","required":True,
              "min_rows":1,"max_rows":30,
              "columns":[{"id":"name","type":"text","required":True},
                         {"id":"value","type":"finite_number","required":True},
                         {"id":"unit","type":"text","required":False},
                         {"id":"low","type":"finite_number","required":True},
                         {"id":"high","type":"finite_number","required":True}]})
    key = field["id"]
    return {"schema_version":"1.0","product_id":pid,"version":"1.0.0",
            "compatible_platform":"morpheus_adaptive_ui",
            "approval_status":"PENDING_VALIDATION",
            "ai_brain":{"role":"Bounded intent","constraints":["No arbitrary code"]},
            "behavioral_contract":{"source_document_ids":["source1"],"requirements":["Isolate context"]},
            "ui_spec":{"allowed_components":["text","input","action","table"],
                       "fields":[field],"action":{"id":"run","adapter":pid,
                       "payload_binding":{key:key}},"result_components":["text","table"]},
            "permissions":{"allowed_actions":["execute"],"external_data":False}}

class CartridgeTests(unittest.TestCase):
    def test_both_candidate_contracts_validate_without_approval(self):
        for pid in ("calculator","hippocrates_labs"):
            with self.subTest(pid=pid):
                c = candidate(pid)
                self.assertIs(validate_cartridge(c,product_id=pid,version="1.0.0"),c)
                self.assertEqual(c["approval_status"],"PENDING_VALIDATION")

    def reject(self, c, code):
        with self.assertRaisesRegex(CartridgeValidationError, code):
            validate_cartridge(c,product_id=c["product_id"],version="1.0.0")

    def test_cross_product_adapter_stops(self):
        c=candidate("calculator");c["ui_spec"]["action"]["adapter"]="hippocrates_labs"
        self.reject(c,"ADAPTER_SCOPE")

    def test_unbound_input_stops(self):
        c=candidate("calculator");c["ui_spec"]["action"]["payload_binding"]={"expression":"other"}
        self.reject(c,"BINDING")

    def test_arbitrary_component_stops(self):
        c=candidate("calculator");c["ui_spec"]["allowed_components"].append("script")
        self.reject(c,"COMPONENTS")

    def test_unbounded_lab_rows_stop(self):
        c=candidate("hippocrates_labs");c["ui_spec"]["fields"][0]["max_rows"]=9999
        self.reject(c,"ROW_BOUND")

    def test_external_data_stops(self):
        c=candidate("hippocrates_labs");c["permissions"]["external_data"]=True
        self.reject(c,"EXTERNAL_DATA")

    def test_missing_contract_stops(self):
        c=candidate("calculator");del c["behavioral_contract"]
        self.reject(c,"BEHAVIOR")

    def test_unhashable_model_input_stops_cleanly(self):
        c=candidate("calculator");c["ui_spec"]["allowed_components"]=[{"type":"script"}]
        self.reject(c,"COMPONENTS")

    def test_wrong_identity_stops(self):
        c=candidate("calculator")
        with self.assertRaisesRegex(CartridgeValidationError,"IDENTITY"):
            validate_cartridge(c,product_id="hippocrates_labs",version="1.0.0")

if __name__=="__main__":
    unittest.main()
