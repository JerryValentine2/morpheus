"""Morpheus's fail-closed Apollo API adapter; no direct GCS/Firestore access.

The approved catalog must be an exact Apollo JSON document. Apollo currently has
no verified list-products endpoint, so discovery is STOP until its catalog document
ID and independently approved digest are configured.
"""
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen


class ApolloRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class Product:
    product_id: str
    display_name: str
    version: str
    artifact_document_id: str
    artifact_sha256: str


class ApolloRegistry:
    def __init__(self, base_url: str, api_key: str, *,
                 catalog_product_id: str = "morpheus_adaptive_ui",
                 catalog_document_id: str = "",
                 catalog_sha256: str = "",
                 timeout: float = 10.0,
                 opener=None):
        parts = urlsplit(base_url)
        if parts.scheme != "https" or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
            raise ApolloRegistryError("INVALID_APOLLO_URL")
        if not isinstance(api_key, str) or not api_key:
            raise ApolloRegistryError("APOLLO_CREDENTIAL_MISSING")
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
            raise ApolloRegistryError("INVALID_TIMEOUT")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.catalog_product_id = catalog_product_id
        self.catalog_document_id = catalog_document_id
        self.catalog_sha256 = catalog_sha256
        self.timeout = timeout
        self.opener = opener or urlopen

    @staticmethod
    def _identifier(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", value):
            raise ApolloRegistryError("INVALID_DOCUMENT_IDENTITY")
        return value

    @staticmethod
    def _digest(value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ApolloRegistryError("INVALID_ARTIFACT_DIGEST")
        return value

    def _exact_document(self, product_id: str, document_id: str, expected_sha256: str):
        product_id = self._identifier(product_id)
        document_id = self._identifier(document_id)
        expected_sha256 = self._digest(expected_sha256)
        url = (self.base_url + "/products/" + quote(product_id, safe="") +
               "/documents/" + quote(document_id, safe="") + "/content")
        req = Request(url, headers={"X-Apollo-Write-Key": self.api_key}, method="GET")
        try:
            with self.opener(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ApolloRegistryError("APOLLO_READ_FAILED")
                # Bound the JSON response; exact content is limited server-side as well.
                payload = response.read(21 * 1024 * 1024 + 1)
                if len(payload) > 21 * 1024 * 1024:
                    raise ApolloRegistryError("APOLLO_RESPONSE_TOO_LARGE")
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise ApolloRegistryError("APOLLO_READ_FAILED") from exc
        try:
            result = json.loads(payload)
            if (not isinstance(result, dict) or result.get("decision") != "PASS" or
                result.get("product_id") != product_id or
                result.get("document_id") != document_id or
                result.get("document_type") != "json"):
                raise ApolloRegistryError("APOLLO_RESPONSE_IDENTITY_MISMATCH")
            content = result.get("content")
            if not isinstance(content, str):
                raise ApolloRegistryError("INVALID_APOLLO_CONTENT")
            actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if (not hmac.compare_digest(actual, expected_sha256) or
                not hmac.compare_digest(actual, self._digest(result.get("sha256")))):
                raise ApolloRegistryError("ARTIFACT_CHECKSUM_MISMATCH")
            return json.loads(content)
        except ApolloRegistryError:
            raise
        except (ValueError, TypeError, UnicodeError) as exc:
            raise ApolloRegistryError("INVALID_APOLLO_CONTENT") from exc

    def list_candidates(self) -> list[dict]:
        """Discover catalog candidates without implying authorization to activate."""
        if not self.catalog_document_id or not self.catalog_sha256:
            raise ApolloRegistryError("APPROVED_APOLLO_CATALOG_NOT_CONFIGURED")
        catalog = self._exact_document(self.catalog_product_id, self.catalog_document_id, self.catalog_sha256)
        if (not isinstance(catalog, dict) or catalog.get("authority") != "apollo" or
            catalog.get("schema_version") != "1.0" or not isinstance(catalog.get("products"), list)):
            raise ApolloRegistryError("INVALID_APOLLO_CATALOG")
        result, seen = [], set()
        for entry in catalog["products"]:
            if not isinstance(entry, dict):
                raise ApolloRegistryError("INVALID_PRODUCT_ENTRY")
            pid = self._identifier(entry.get("product_id"))
            version = self._identifier(entry.get("version"))
            label = entry.get("display_name")
            if not isinstance(label, str) or not label.strip() or (pid, version) in seen:
                raise ApolloRegistryError("INVALID_PRODUCT_ENTRY")
            seen.add((pid, version))
            result.append({"product_id": pid, "display_name": label.strip(), "version": version,
                           "approved": entry.get("approved") is True,
                           "activation_enabled": entry.get("activation_enabled") is True})
        return result

    def list_products(self) -> list[Product]:
        # A digest pinned outside the retrieved catalog prevents a forged catalog
        # from granting its own approval. No configured catalog = no activation.
        if not self.catalog_document_id or not self.catalog_sha256:
            raise ApolloRegistryError("APPROVED_APOLLO_CATALOG_NOT_CONFIGURED")
        catalog = self._exact_document(self.catalog_product_id, self.catalog_document_id, self.catalog_sha256)
        if (not isinstance(catalog, dict) or catalog.get("authority") != "apollo" or
            catalog.get("schema_version") != "1.0" or
            not isinstance(catalog.get("products"), list)):
            raise ApolloRegistryError("INVALID_APOLLO_CATALOG")
        result, seen = [], set()
        for entry in catalog["products"]:
            if not isinstance(entry, dict):
                raise ApolloRegistryError("INVALID_PRODUCT_ENTRY")
            identity = (entry.get("product_id"), entry.get("version"))
            if identity in seen:
                raise ApolloRegistryError("DUPLICATE_PRODUCT_VERSION")
            seen.add(identity)
            if entry.get("approved") is not True or entry.get("activation_enabled") is not True:
                continue
            try:
                p = Product(*(entry[k] for k in (
                    "product_id", "display_name", "version",
                    "artifact_document_id", "artifact_sha256")))
            except (KeyError, TypeError) as exc:
                raise ApolloRegistryError("INVALID_PRODUCT_ENTRY") from exc
            for value in (p.product_id, p.version, p.artifact_document_id):
                self._identifier(value)
            if not isinstance(p.display_name, str) or not p.display_name.strip():
                raise ApolloRegistryError("INVALID_PRODUCT_ENTRY")
            self._digest(p.artifact_sha256)
            result.append(p)
        return result

    def get_product_artifact(self, product_id: str, version: str) -> dict:
        matches = [p for p in self.list_products()
                   if p.product_id == product_id and p.version == version]
        if len(matches) != 1:
            raise ApolloRegistryError("UNKNOWN_OR_UNAPPROVED_PRODUCT_VERSION")
        p = matches[0]
        artifact = self._exact_document(p.product_id, p.artifact_document_id, p.artifact_sha256)
        if not isinstance(artifact, dict):
            raise ApolloRegistryError("INVALID_AI_CARTRIDGE")
        if artifact.get("product_id") != p.product_id or artifact.get("version") != p.version:
            raise ApolloRegistryError("ARTIFACT_IDENTITY_MISMATCH")
        if not artifact.get("ai_brain") or not artifact.get("ui_spec"):
            raise ApolloRegistryError("INCOMPLETE_AI_CARTRIDGE")
        if "agents" in artifact and (
            not isinstance(artifact["agents"], list) or not artifact["agents"] or
            any(not isinstance(a, dict) or not isinstance(a.get("id"), str) or
                not a["id"].strip() for a in artifact["agents"])):
            raise ApolloRegistryError("INVALID_AGENT_CONTRACT")
        if "permissions" in artifact and not isinstance(artifact["permissions"], dict):
            raise ApolloRegistryError("INVALID_PERMISSIONS")
        if "behavioral_contract" in artifact and not artifact["behavioral_contract"]:
            raise ApolloRegistryError("INVALID_BEHAVIORAL_CONTRACT")
        if artifact.get("compatible_platform", "morpheus_adaptive_ui") != "morpheus_adaptive_ui":
            raise ApolloRegistryError("INCOMPATIBLE_PLATFORM")
        return artifact
