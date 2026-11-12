"""Explicit, digest-pinned development-only Apollo cartridge access.

This is a separate development evaluation gate, never catalog approval or
production activation. The operator must explicitly opt in to each immutable
artifact by document ID and independently verified SHA-256.
"""
import os
import re

from apollo_registry import ApolloRegistryError
from cartridge_validation import validate_cartridge, CartridgeValidationError

CANDIDATES = {
    "calculator": ("458aa88001ed4c369f662a934712784e",
                   "70fb3330cf428c09fd26162c2aa86e7158934f3d758347d026be9af6ebb47406"),
    "hippocrates_labs": ("f7c8097a2fad4815a54fe37f22700445",
                         "fcf5943cdde4e4bc4f0afcc1e8ea1846a71cc1c1f20cd2175c07f555176d0e14"),
}
DIGEST = re.compile(r"^[0-9a-f]{64}$")


def get_development_cartridge(registry, product_id, version, *, environ=None):
    env = os.environ if environ is None else environ
    if env.get("MORPHEUS_ENV") != "development":
        raise ApolloRegistryError("DEVELOPMENT_CARTRIDGE_ENV_STOP")
    if env.get("MORPHEUS_DEV_CARTRIDGES_ENABLED") != "true":
        raise ApolloRegistryError("DEVELOPMENT_CARTRIDGE_DISABLED")
    if version != "1.0.0" or product_id not in CANDIDATES:
        raise ApolloRegistryError("DEVELOPMENT_CARTRIDGE_UNKNOWN")
    doc_id, digest = CANDIDATES[product_id]
    # Explicitly configured digest must match the independently captured
    # verification result. No fallback to server-provided checksum or catalog.
    configured = env.get("MORPHEUS_DEV_" + product_id.upper() + "_SHA256", "")
    if not DIGEST.fullmatch(configured) or configured != digest:
        raise ApolloRegistryError("DEVELOPMENT_CARTRIDGE_PIN_STOP")
    artifact = registry._exact_document(product_id, doc_id, digest)
    try:
        validate_cartridge(artifact, product_id=product_id, version=version)
    except CartridgeValidationError as exc:
        raise ApolloRegistryError(str(exc)) from exc
    if artifact.get("approval_status") != "PENDING_VALIDATION":
        raise ApolloRegistryError("DEVELOPMENT_CARTRIDGE_STATUS_STOP")
    return artifact
