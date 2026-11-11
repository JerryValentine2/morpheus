"""Morpheus Apollo discovery and AI preview workflow. Apollo/AI functions injected.
No GCS, GitHub registry, or product-specific Python intent enums.
Search chunks permit discovery/preview, NOT approved runtime activation.
"""
import re
from ui_validation import validate_ui_parts, UIValidationError
from dataclasses import dataclass

class FlowStop(RuntimeError): pass

@dataclass(frozen=True)
class ProductOption:
    label: str
    product_id: str

class MorpheusFlow:
    def __init__(self, apollo_search, ai_reason):
        self.search = apollo_search
        self.ai = ai_reason
        self.options = ()

    def discover(self):
        result = self.search(product_id="morpheus_adaptive_ui", query="Morpheus Product Selector Registry V1 Calculator Hippocrates Labs display_name product_id")
        if result.get("decision") != "PASS": raise FlowStop("APOLLO_DISCOVERY_FAILED")
        hits = [r for r in result.get("results", []) if r.get("document_id") == "f93144ea664b494094cee9e1debb2e0f" and r.get("product_id") == "morpheus_adaptive_ui"]
        if len(hits) != 1: raise FlowStop("REGISTRY_NOT_UNAMBIGUOUS")
        pairs = re.findall(r"display_name:\s*([^\n]+?)\s+product_id:\s*([a-z][a-z0-9_]*)", hits[0]["content"])
        if not pairs or len({pid for _, pid in pairs}) != len(pairs): raise FlowStop("INVALID_REGISTRY")
        self.options = tuple(ProductOption(label.strip(), pid) for label, pid in pairs)
        return [{"label": p.label, "value": p.product_id} for p in self.options]

    def ask(self, product_id, user_message):
        if product_id not in {p.product_id for p in self.options}: raise FlowStop("UNKNOWN_PRODUCT")
        if not isinstance(user_message, str) or not user_message.strip(): raise FlowStop("EMPTY_MESSAGE")
        def retrieve(query):
            result = self.search(product_id=product_id, query=query)
            if not isinstance(result, dict) or result.get("decision") != "PASS" or result.get("product_id", product_id) != product_id:
                raise FlowStop("APOLLO_PRODUCT_SEARCH_FAILED")
            return [{"document_id":r["document_id"],"content":r["content"][:12000]} for r in result.get("results", [])
                    if isinstance(r, dict) and r.get("product_id") == product_id
                    and isinstance(r.get("document_id"), str) and isinstance(r.get("content"), str) and r["content"]][:8]
        context = retrieve("AI brain contract adaptive UI components web parts response to: " + user_message[:300])
        if not context: raise FlowStop("NO_PRODUCT_KNOWLEDGE")
        for round_number in range(3):
            response = self.ai(product_id=product_id, user_message=user_message, context=context,
                instruction="Use product-scoped Apollo evidence. Return preview with safe UI parts, stop, or needs_more_context with search_query. Never claim activation.")
            if not isinstance(response, dict) or response.get("status") not in ("preview", "needs_more_context", "stop"):
                raise FlowStop("INVALID_AI_RESPONSE")
            if response["status"] == "preview":
                parts = response.get("ui_parts")
                try:
                    validate_ui_parts(parts)
                except UIValidationError as exc:
                    raise FlowStop("INVALID_UI_PARTS: " + str(exc)) from exc
                return response
            if response["status"] == "stop": return response
            if round_number == 2: raise FlowStop("RETRIEVAL_LIMIT")
            query = response.get("search_query")
            if not isinstance(query, str) or not query.strip() or len(query) > 300:
                raise FlowStop("INVALID_FOLLOWUP_QUERY")
            seen = {r["document_id"] for r in context}
            extra = [r for r in retrieve(query) if r["document_id"] not in seen]
            if not extra: raise FlowStop("NO_NEW_CONTEXT")
            context = (context + extra)[:12]
        raise FlowStop("RETRIEVAL_LIMIT")
