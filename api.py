"""Morpheus Flask preview API. Simulated Apollo/AI; no production activation."""
import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
from apollo_flow import MorpheusFlow, FlowStop
from environment import load_environment

REGISTRY = "display_name: Calculator product_id: calculator\ndisplay_name: Hippocrates Labs product_id: hippocrates_labs"
DOCS = {
    "calculator": [
        ("9032a125bfd2447e8ac8725ca3179787", "AI brain interprets math questions, requests safe UI; candidate only."),
        ("291c70cec4d941a59406da5fd7dca63b", "UI: calculation input, action, result text; no executable UI.")
    ],
    "hippocrates_labs": [
        ("08e574d118504332a5368a10612edd51", "AI interprets synthetic lab questions; text, table, chart; no diagnosis."),
        ("7cbef5aab9304d42a75b3ca7d5264afc", "Synthetic lab fixture WBC 7.2 x10^3/uL; candidate only.")
    ]
}

def simulated_apollo_search(product_id, query):
    if product_id == "morpheus_adaptive_ui":
        return {"decision": "PASS", "product_id": product_id, "results": [
            {"product_id": product_id, "document_id": "f93144ea664b494094cee9e1debb2e0f", "content": REGISTRY}
        ]}
    # Simulate separate brain and UI retrievals, matching the Apollo request boundary.
    docs = DOCS.get(product_id, [])
    is_ui_followup = query.startswith("UI components web parts for ")
    selected = docs[1:2] if is_ui_followup else docs[:1]
    return {"decision": "PASS", "product_id": product_id, "results": [
        {"product_id": product_id, "document_id": did, "content": content}
        for did, content in selected
    ]}

def simulated_ai_reason(product_id, user_message, context, instruction):
    """A deterministic preview stub, NOT a real LLM or verified domain computation."""
    if len(context) < 2:
        return {"status": "needs_more_context",
                "search_query": "UI components web parts for " + product_id}
    if product_id == "calculator":
        return {"status": "preview", "ui_parts": [
            {"type": "text", "content": "Calculator preview (AI simulated; no computation performed)."},
            {"type": "input", "label": "Calculation"},
            {"type": "action", "label": "Calculate"}
        ], "source_document_ids": [x["document_id"] for x in context]}
    return {"status": "preview", "ui_parts": [
        {"type": "text", "content": "Hippocrates Labs: synthetic demonstration only."},
        {"type": "table", "columns": ["Measurement", "Value", "Units"], "rows": [["WBC", "7.2", "10^3/uL"]]}
    ], "source_document_ids": [x["document_id"] for x in context]}

def create_app(search=None, ai=None):
    config = load_environment()
    if config["environment"] == "production":
        # Live Apollo and AI adapters are not yet implemented or validated.
        # Never allow a production instance to silently serve simulated data.
        raise RuntimeError("PRODUCTION_STOP: real Apollo and AI adapters are not implemented")
    app = Flask(__name__, static_folder="web")
    flow = MorpheusFlow(search or simulated_apollo_search, ai or simulated_ai_reason)

    @app.get("/")
    def index():
        return send_from_directory("web", "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "mode": "SIMULATED", "production_activation": False})

    @app.get("/api/products")
    def products():
        try:
            return jsonify({"mode": "SIMULATED", "products": flow.discover(), "activation_enabled": False})
        except FlowStop as exc:
            return jsonify({"error": str(exc)}), 409

    @app.post("/api/preview")
    def preview():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "INVALID_JSON"}), 400
        try:
            # Discover on each request: no cross-request active product or shared session.
            flow.discover()
            result = flow.ask(data.get("product_id"), data.get("message"))
            return jsonify({"mode": "SIMULATED", "product_id": data.get("product_id"),
                            "activation_enabled": False, "result": result})
        except FlowStop as exc:
            return jsonify({"error": str(exc)}), 422

    return app

app = create_app()
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8080")), debug=False)
