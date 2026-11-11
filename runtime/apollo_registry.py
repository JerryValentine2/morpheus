"""Apollo authoritative catalog and exact cartridge access; GCS registry is trusted, vector search is not."""
import hashlib
import json
import re
from dataclasses import dataclass
from google.cloud import storage

class ApolloRegistryError(RuntimeError):
    pass

@dataclass(frozen=True)
class Product:
    product_id: str
    display_name: str
    version: str
    artifact_object: str
    artifact_sha256: str

class ApolloRegistry:
    def __init__(self, bucket: str, catalog_object: str = "registry/products.v1.json", client=None):
        if not isinstance(bucket, str) or not bucket.strip():
            raise ApolloRegistryError("INVALID_BUCKET")
        self.bucket = bucket
        self.catalog_object = catalog_object
        self.client = client if client is not None else storage.Client()

    def _read(self, name: str) -> bytes:
        if not isinstance(name, str) or not name or name.startswith("/") or ".." in name.split("/") or chr(92) in name:
            raise ApolloRegistryError("INVALID_OBJECT_PATH")
        try:
            return self.client.bucket(self.bucket).blob(name).download_as_bytes()
        except Exception as exc:
            raise ApolloRegistryError("APOLLO_READ_FAILED") from exc

    def list_products(self) -> list[Product]:
        try:
            catalog = json.loads(self._read(self.catalog_object))
            if not isinstance(catalog, dict) or catalog.get("authority") != "apollo" or catalog.get("schema_version") != "1.0" or not isinstance(catalog.get("products"), list):
                raise ApolloRegistryError("INVALID_APOLLO_CATALOG")
            result, seen = [], set()
            for entry in catalog["products"]:
                if not isinstance(entry, dict) or not isinstance(entry.get("product_id"), str):
                    raise ApolloRegistryError("INVALID_PRODUCT_ENTRY")
                identity = (entry["product_id"], entry.get("version"))
                if identity in seen:
                    raise ApolloRegistryError("DUPLICATE_PRODUCT_VERSION")
                seen.add(identity)
                if entry.get("approved") is not True or entry.get("activation_enabled") is not True:
                    continue
                p = Product(*(entry[k] for k in ("product_id", "display_name", "version", "artifact_object", "artifact_sha256")))
                if not all(isinstance(v, str) and v.strip() for v in vars(p).values()) or not re.fullmatch(r"[0-9a-f]{64}", p.artifact_sha256):
                    raise ApolloRegistryError("INVALID_PRODUCT_ENTRY")
                result.append(p)
            return result
        except ApolloRegistryError:
            raise
        except Exception as exc:
            raise ApolloRegistryError("INVALID_APOLLO_CATALOG") from exc

    def get_product_artifact(self, product_id: str, version: str) -> dict:
        matches = [p for p in self.list_products() if p.product_id == product_id and p.version == version]
        if len(matches) != 1:
            raise ApolloRegistryError("UNKNOWN_OR_UNAPPROVED_PRODUCT_VERSION")
        p = matches[0]
        raw = self._read(p.artifact_object)
        if hashlib.sha256(raw).hexdigest() != p.artifact_sha256:
            raise ApolloRegistryError("ARTIFACT_CHECKSUM_MISMATCH")
        try:
            artifact = json.loads(raw)
            if not isinstance(artifact, dict):
                raise ApolloRegistryError("INVALID_AI_CARTRIDGE")
            if artifact.get("product_id") != p.product_id or artifact.get("version") != p.version:
                raise ApolloRegistryError("ARTIFACT_IDENTITY_MISMATCH")
            if not artifact.get("ai_brain") or not artifact.get("ui_spec"):
                raise ApolloRegistryError("INCOMPLETE_AI_CARTRIDGE")
            if "agents" in artifact and (not isinstance(artifact["agents"], list) or not artifact["agents"] or any(not isinstance(a, dict) or not isinstance(a.get("id"), str) or not a["id"].strip() for a in artifact["agents"])):
                raise ApolloRegistryError("INVALID_AGENT_CONTRACT")
            if "permissions" in artifact and not isinstance(artifact["permissions"], dict):
                raise ApolloRegistryError("INVALID_PERMISSIONS")
            if "behavioral_contract" in artifact and not artifact["behavioral_contract"]:
                raise ApolloRegistryError("INVALID_BEHAVIORAL_CONTRACT")
            if "compatible_platform" in artifact and artifact["compatible_platform"] != "morpheus_adaptive_ui":
                raise ApolloRegistryError("INCOMPATIBLE_PLATFORM")
            return artifact
        except ApolloRegistryError:
            raise
        except Exception as exc:
            raise ApolloRegistryError("INVALID_AI_CARTRIDGE") from exc
