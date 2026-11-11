"""One-request Gemini live smoke test in Google Cloud Shell.

Run with Application Default Credentials in an authorized GCP project.
Prints a sanitized PASS/STOP report; does not print credentials.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
from gemini_adapter import make_gemini_reasoner, GeminiAdapterError

def main():
    model = os.environ.get("MORPHEUS_GEMINI_MODEL")
    if not model:
        print("STOP: MORPHEUS_GEMINI_MODEL is required")
        return 2
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("STOP: GOOGLE_CLOUD_PROJECT is required")
        return 2
    try:
        reason = make_gemini_reasoner(model=model)
        result = reason(
            product_id="calculator",
            user_message="Show a text-only preview that says: Gemini live connection verified.",
            context=[{"document_id": "live-smoke-synthetic",
                      "content": "Synthetic smoke-test evidence only. A text-only preview is permitted. No real Apollo data."}],
            instruction="For this connectivity test, return a preview with one text UI part. Do not activate anything.",
        )
        if result.get("status") != "preview":
            print("STOP: Gemini returned status:", result.get("status"))
            return 1
        from ui_validation import validate_ui_parts
        validate_ui_parts(result.get("ui_parts"))
        print(json.dumps({"decision": "PASS", "model": model,
                          "status": result["status"], "ui_parts": result["ui_parts"],
                          "apollo": "synthetic_only", "activation": False}))
        return 0
    except (GeminiAdapterError, Exception) as exc:
        print(json.dumps({"decision": "STOP", "error_type": type(exc).__name__,
                          "error": str(exc)[:300]}))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
