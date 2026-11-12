"""Morpheus Flask preview API. Simulated Apollo/AI; no production activation."""
import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
sys.path.insert(0, str(Path(__file__).resolve().parent / "runtime"))
from apollo_flow import MorpheusFlow, FlowStop
from types import SimpleNamespace
from environment import load_environment
from apollo_registry import ApolloRegistry, ApolloRegistryError
from product_execution import execute, ProductExecutionError
from gemini_adapter import make_gemini_reasoner, GeminiAdapterError
from ui_validation import validate_ui_parts, UIValidationError
from development_cartridges import get_development_cartridge


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

class SimulatedRegistry:
    """Development-only product fixture; never authoritative or production enabled."""
    def list_products(self):
        return [SimpleNamespace(product_id="calculator", display_name="Calculator"),
                SimpleNamespace(product_id="hippocrates_labs", display_name="Hippocrates Labs")]

def configured_apollo_registry():
    """Read exact Apollo catalog identity from configuration; never embed credentials."""
    if os.environ.get("MORPHEUS_REGISTRY_MODE", "simulated") != "apollo":
        return None
    key = os.environ.get("APOLLO_WRITE_KEY", "")
    return ApolloRegistry(
        os.environ.get("APOLLO_BASE_URL", "https://apollo-vector-database-service-927115364189.us-central1.run.app"),
        key,
        catalog_document_id=os.environ.get("APOLLO_CATALOG_DOCUMENT_ID", "177030db19704abaa93059dcf10c7172"),
        catalog_sha256=os.environ.get("APOLLO_CATALOG_SHA256", "f9e600689c48ae459ceb7fc4bcdf67d3089f55ab5ae5340a91ac229fe3b8f1b7"),
    )


def create_app(search=None, ai=None, registry=None):
    config = load_environment()
    if config["environment"] == "production":
        # Live Apollo and AI adapters are not yet implemented or validated.
        # Never allow a production instance to silently serve simulated data.
        raise RuntimeError("PRODUCTION_STOP: real Apollo and AI adapters are not implemented")
    live_registry = configured_apollo_registry() if registry is None else None
    selected_registry = registry if registry is not None else (live_registry or SimulatedRegistry())
    registry_mode = "APOLLO_CATALOG" if live_registry is not None else "SIMULATED"
    app = Flask(__name__, static_folder="web")
    flow = MorpheusFlow(search or simulated_apollo_search, ai or simulated_ai_reason, registry=selected_registry)

    @app.get("/")
    def index():
        return send_from_directory("web", "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "mode": registry_mode, "production_activation": False})

    @app.get("/api/products")
    def products():
        try:
            return jsonify({"mode": registry_mode, "products": flow.discover(), "activation_enabled": False})
        except (FlowStop, ApolloRegistryError) as exc:
            return jsonify({"error": str(exc)}), 409

    @app.get("/api/candidates")
    def candidates():
        if live_registry is None:
            return jsonify({"error": "APOLLO_CATALOG_NOT_CONFIGURED"}), 409
        try:
            entries = live_registry.list_candidates()
            return jsonify({"mode": "APOLLO_CATALOG", "products": entries,
                            "production_activation": False})
        except ApolloRegistryError as exc:
            return jsonify({"error": str(exc)}), 409

    @app.post("/api/adaptive-plan")
    def adaptive_plan():
        """Development-only live AI plan, gated by an approved Apollo artifact.

        A plan is untrusted display data, not permission to execute a product.
        """
        if live_registry is None:
            return jsonify({"error": "APOLLO_CATALOG_NOT_CONFIGURED"}), 409
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "INVALID_JSON"}), 400
        pid, version, message = data.get("product_id"), data.get("version"), data.get("message")
        if (not isinstance(pid, str) or not pid or not isinstance(version, str) or
                not version or not isinstance(message, str) or not 0 < len(message.strip()) <= 4000):
            return jsonify({"error": "INVALID_ADAPTIVE_REQUEST"}), 400
        try:
            # Development evaluation requires an explicit, independently pinned
            # candidate gate; no catalog approval or production activation.
            if os.environ.get('MORPHEUS_DEV_CARTRIDGES_ENABLED') == 'true':
                artifact = get_development_cartridge(live_registry, pid, version)
            else:
                artifact = live_registry.get_product_artifact(pid, version)
            evidence = [{"document_id": artifact.get("document_id", "approved_artifact"),
                         "content": __import__("json").dumps({
                             "ai_brain": artifact["ai_brain"],
                             "ui_spec": artifact["ui_spec"],
                             "behavioral_contract": artifact.get("behavioral_contract"),
                             "permissions": artifact.get("permissions"),
                         }, ensure_ascii=False)}]
            reasoner = make_gemini_reasoner()
            plan = reasoner(product_id=pid, user_message=message, context=evidence,
                            instruction="Propose only validated display UI components from the approved Apollo artifact. "
                                        "Return JSON status preview with ui_parts or stop. "
                                        "No diagnosis, no executable HTML or JavaScript, no product execution.")
            if plan.get("status") != "preview":
                return jsonify({"error": "AI_PLAN_STOP", "status": plan.get("status")}), 409
            parts = validate_ui_parts(plan.get("ui_parts"))
            # Never echo model-supplied source identities; provenance comes from the registry.
            return jsonify({"mode": "LIVE_AI_DEVELOPMENT", "production_activation": False,
                            "product_id": pid, "version": version,
                            "ui_parts": parts, "executable": False})
        except (ApolloRegistryError, GeminiAdapterError, UIValidationError, ValueError, TypeError) as exc:
            # Fail closed. Do not leak provider or retrieved artifact content.
            code = str(exc) if isinstance(exc, (ApolloRegistryError, GeminiAdapterError, UIValidationError)) else "INVALID_ARTIFACT"
            return jsonify({"error": code}), 409

    @app.post("/api/execute")
    def execute_product():
        # Functional development path: requires real Apollo catalog identity,
        # never authorizes a production release or unvalidated AI cartridge.
        if live_registry is None:
            return jsonify({"error": "APOLLO_CATALOG_NOT_CONFIGURED"}), 409
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "INVALID_JSON"}), 400
        pid = data.get("product_id")
        try:
            catalog = live_registry.list_candidates()
            if pid not in {p["product_id"] for p in catalog}:
                return jsonify({"error": "UNKNOWN_APOLLO_PRODUCT"}), 422
            result = execute(pid, data)
            return jsonify({"mode": "FUNCTIONAL_DEVELOPMENT", "production_activation": False,
                            "result": result})
        except (ApolloRegistryError, ProductExecutionError) as exc:
            return jsonify({"error": str(exc)}), 422

    @app.post("/api/preview")
    def preview():
        if live_registry is not None:
            return jsonify({"error": "APOLLO_CATALOG_PREVIEW_DISABLED_PENDING_REAL_AI_ADAPTER"}), 409
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
