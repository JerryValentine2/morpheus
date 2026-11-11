"""Apollo authoritative catalog and exact cartridge access. No local product registry.
Requires google-cloud-storage and IAM read permission to the Apollo GCS bucket.
The catalog object must be published by Apollo's governed registry process.
"""
import hashlib
import json
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
        self.bucket = bucket
        self.catalog_object = catalog_object
        self.client = client or storage.Client()

    def _read(self, name: str) -> bytes:
        if not name or name.startswith("/") or ".." in name.split("/"):
            raise ApolloRegistryError("INVALID_OBJECT_PATH")
        blob = self.client.bucket(self.bucket).blob(name)
        try:
            return blob.download_as_bytes()
        except Exception as exc:
            raise ApolloRegistryError("APOLLO_READ_FAILED") from exc

    def list_products(self) -> list[Product]:
        try:
            catalog = json.loads(self._read(self.catalog_object))
            if catalog["authority"] != "apollo" or catalog["schema_version"] != "1.0":
                raise ApolloRegistryError("INVALID_APOLLO_CATALOG")
            entries = catalog["products"]
            if not isinstance(entries, list):
                raise ApolloRegistryError("INVALID_APOLLO_CATALOG")
            result = []
            seen = set()
            for p in entries:
                if p["product_id"] in seen:
                    raise ApolloRegistryError("DUPLICATE_PRODUCT")
                seen.add(p["product_id"])
                if p.get("approved") is True and p.get("activation_enabled") is True:
                    record = Product(*(p[k] for k in ("product_id", "display_name", "version", "artifact_object", "artifact_sha256")))
                    if not all(vars(record).values()) or len(record.artifact_sha256) != 64:
                        raise ApolloRegistryError("INVALID_PRODUCT_ENTRY")
                    result.append(record)
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
            if artifact["product_id"] != p.product_id or artifact["version"] != p.version:
                raise ApolloRegistryError("ARTIFACT_IDENTITY_MISMATCH")
            if not artifact.get("ai_brain") or not artifact.get("ui_spec"):
                raise ApolloRegistryError("INCOMPLETE_AI_CARTRIDGE")
            return artifact
        except ApolloRegistryError:
            raise
        except Exception as exc:
            raise ApolloRegistryError("INVALID_AI_CARTRIDGE") from exc
