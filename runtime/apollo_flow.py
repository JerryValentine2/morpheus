"""Morpheus Apollo discovery and AI preview workflow. Apollo/AI functions injected.
No GCS, GitHub registry, or product-specific Python intent enums.
Search chunks permit discovery/preview, NOT approved runtime activation.
"""
import re
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
        result = self.search(product_id=product_id, query="AI brain contract adaptive UI components web parts response to: " + user_message[:300])
        if result.get("decision") != "PASS": raise FlowStop("APOLLO_PRODUCT_SEARCH_FAILED")
        hits = [r for r in result.get("results", []) if r.get("product_id") == product_id and r.get("content")]
        if not hits: raise FlowStop("NO_PRODUCT_KNOWLEDGE")
        context = [{"document_id":r["document_id"],"content":r["content"]} for r in hits[:5]]
        response = self.ai(product_id=product_id,user_message=user_message,context=context,instruction="Use product-scoped Apollo evidence. Interpret intent and propose safe UI parts. If insufficient, request more context. No invented data, executable UI or activation claims.")
        if not isinstance(response,dict) or response.get("status") not in ("preview","needs_more_context","stop"): raise FlowStop("INVALID_AI_RESPONSE")
        if response["status"] == "preview":
            parts = response.get("ui_parts")
            if not isinstance(parts,list) or any(not isinstance(p,dict) or p.get("type") not in ("text","table","chart","input","action") for p in parts): raise FlowStop("INVALID_UI_PARTS")
        return response
