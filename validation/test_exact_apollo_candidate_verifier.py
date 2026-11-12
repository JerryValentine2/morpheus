"""Offline verification of the exact-document verifier's integrity and STOP behavior."""
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_apollo_candidates import verify_one

class Response:
    status = 200
    def __init__(self, data):
        self.buffer = io.BytesIO(json.dumps(data).encode())
    def __enter__(self): return self
    def __exit__(self, *args): self.buffer.close()
    def read(self, n=-1): return self.buffer.read(n)

def cartridge():
    return {"schema_version":"1.0","product_id":"calculator","version":"1.0.0",
            "compatible_platform":"morpheus_adaptive_ui","approval_status":"PENDING_VALIDATION",
            "ai_brain":{"role":"arithmetic","constraints":["no code"]},
            "behavioral_contract":{"source_document_ids":["source"],"requirements":["safe"]},
            "ui_spec":{"allowed_components":["text","input","action","table"],
                       "fields":[{"id":"expression","label":"Calculation","type":"text",
                                  "required":True,"max_length":200}],
                       "action":{"id":"calculate","adapter":"calculator",
                                 "payload_binding":{"expression":"expression"}},
                       "result_components":["text"]},
            "permissions":{"allowed_actions":["calculator:compute"],"external_data":False}}

class VerifyTests(unittest.TestCase):
    def payload(self, *, tamper=False, wrong_identity=False, bad_schema=False):
        a=cartridge()
        if bad_schema:
            a["ui_spec"]["action"]["adapter"]="hippocrates_labs"
        content=json.dumps(a)
        return {"decision":"PASS","product_id":"other" if wrong_identity else "calculator",
                "document_id":"doc","document_type":"json","content":content,
                "sha256":"0"*64 if tamper else hashlib.sha256(content.encode()).hexdigest()}

    def run_verify(self, **kwargs):
        return verify_one("calculator","doc","test-key",
                          opener=lambda request,timeout:Response(self.payload(**kwargs)))

    def test_exact_hash_and_contract_pass_without_approval(self):
        result=self.run_verify()
        self.assertEqual(result["schema_validation"],"PASS")
        self.assertEqual(result["approval"],"NOT_GRANTED")
        self.assertFalse(result["activation"])

    def test_hash_mismatch_stops(self):
        with self.assertRaisesRegex(ValueError,"SHA256_MISMATCH"):
            self.run_verify(tamper=True)

    def test_wrong_identity_stops(self):
        with self.assertRaisesRegex(ValueError,"IDENTITY_MISMATCH"):
            self.run_verify(wrong_identity=True)

    def test_invalid_cartridge_stops(self):
        with self.assertRaisesRegex(ValueError,"CARTRIDGE_VALIDATION_FAILED"):
            self.run_verify(bad_schema=True)

if __name__=="__main__":
    unittest.main()
