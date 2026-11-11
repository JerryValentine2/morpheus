"""Validated Morpheus environment configuration; production fails closed."""
import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"development": "dev.yaml", "production": "prod.yaml"}

def load_environment(name=None):
    name = name or os.environ.get("MORPHEUS_ENV", "development")
    if name not in ALLOWED:
        raise RuntimeError("MORPHEUS_ENV must be development or production")
    path = ROOT / "config" / ALLOWED[name]
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("environment") != name:
        raise RuntimeError("Invalid Morpheus environment configuration")
    if config.get("server", {}).get("framework") != "flask":
        raise RuntimeError("Unsupported server configuration")
    validation = config.get("validation", {})
    if validation.get("strict") is not True or validation.get("activation_enabled") is not False:
        raise RuntimeError("Unsafe Morpheus validation configuration")
    apollo = config.get("apollo", {}).get("adapter")
    ai = config.get("ai", {}).get("adapter")
    expected = ("simulated", "simulated") if name == "development" else ("gcp_authenticated", "live")
    if (apollo, ai) != expected:
        raise RuntimeError("Morpheus adapter configuration mismatch")
    return config
