"""Verify exact Apollo candidate artifacts without granting runtime approval.

Usage (from a credentialed operator environment):
    APOLLO_WRITE_KEY=<provided securely by environment> python tools/verify_apollo_candidates.py
Never paste or commit a secret. The script does not print the key or document content.
"""
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from cartridge_validation import validate_cartridge, CartridgeValidationError

BASE_URL = "https://apollo-vector-database-service-927115364189.us-central1.run.app"
DOCUMENTS = (
    ("calculator", "458aa88001ed4c369f662a934712784e"),
    ("hippocrates_labs", "f7c8097a2fad4815a54fe37f22700445"),
)

def verify_one(product_id, document_id, key, *, opener=urlopen):
    url = (BASE_URL + "/products/" + quote(product_id, safe="") +
           "/documents/" + quote(document_id, safe="") + "/content")
    req = Request(url, headers={"X-Apollo-Write-Key": key}, method="GET")
    try:
        with opener(req, timeout=20) as response:
            if response.status != 200:
                raise ValueError("APOLLO_HTTP_NOT_OK")
            raw = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise ValueError("APOLLO_EXACT_READ_FAILED") from exc
    if len(raw) > 1024 * 1024:
        raise ValueError("APOLLO_RESPONSE_TOO_LARGE")
    try:
        payload = json.loads(raw)
        if (not isinstance(payload, dict) or payload.get("decision") != "PASS" or
            payload.get("product_id") != product_id or
            payload.get("document_id") != document_id or
            payload.get("document_type") != "json"):
            raise ValueError("APOLLO_IDENTITY_MISMATCH")
        content = payload.get("content")
        if not isinstance(content, str):
            raise ValueError("APOLLO_CONTENT_INVALID")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if payload.get("sha256") != digest:
            raise ValueError("APOLLO_SHA256_MISMATCH")
        artifact = json.loads(content)
        validate_cartridge(artifact, product_id=product_id, version="1.0.0")
        if artifact.get("approval_status") != "PENDING_VALIDATION":
            raise ValueError("UNEXPECTED_CANDIDATE_APPROVAL_STATUS")
        return {"product_id": product_id, "document_id": document_id,
                "sha256": digest, "schema_validation": "PASS",
                "approval": "NOT_GRANTED", "activation": False}
    except (json.JSONDecodeError, TypeError, UnicodeError) as exc:
        raise ValueError("APOLLO_CONTENT_INVALID") from exc
    except CartridgeValidationError as exc:
        raise ValueError("CARTRIDGE_VALIDATION_FAILED:" + str(exc)) from exc

def main():
    key = os.environ.get("APOLLO_WRITE_KEY")
    if not key:
        print(json.dumps({"decision": "STOP", "error": "APOLLO_CREDENTIAL_MISSING"}))
        return 2
    results = []
    for pid, did in DOCUMENTS:
        try:
            results.append(verify_one(pid, did, key))
        except ValueError as exc:
            print(json.dumps({"decision": "STOP", "product_id": pid, "error": str(exc)}))
            return 1
    print(json.dumps({"decision": "PASS", "scope": "EXACT_DOCUMENT_AND_SCHEMA_ONLY",
                      "production_activation": False, "artifacts": results}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
