"""Fail-closed validation of declarative Apollo AI/UI cartridge contracts.

Validation checks structural safety only. It NEVER grants approval or activation.
"""
import re

class CartridgeValidationError(ValueError):
    pass

ID = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
COMPONENTS = {"text", "input", "action", "table"}
FIELD_TYPES = {"text", "measurement_rows"}
CELL_TYPES = {"text", "finite_number"}
ADAPTERS = {"calculator", "hippocrates_labs"}

def _stop(code):
    raise CartridgeValidationError(code)

def _identifier(value):
    return isinstance(value, str) and bool(ID.fullmatch(value))

def _strings(values, allowed=None):
    return (isinstance(values, list) and bool(values) and
            len(values) == len(set(values)) and
            all(isinstance(x, str) and (allowed is None or x in allowed) for x in values))

def validate_cartridge(artifact, *, product_id, version):
    """Return validated data, never a product activation decision."""
    if not isinstance(artifact, dict) or artifact.get("schema_version") != "1.0":
        _stop("CARTRIDGE_SCHEMA_VERSION")
    if artifact.get("product_id") != product_id or artifact.get("version") != version:
        _stop("CARTRIDGE_IDENTITY")
    if artifact.get("compatible_platform") != "morpheus_adaptive_ui":
        _stop("CARTRIDGE_PLATFORM")
    if artifact.get("approval_status") not in ("PENDING_VALIDATION", "APPROVED"):
        _stop("CARTRIDGE_APPROVAL_STATUS")
    brain, behavior, ui, permissions = (artifact.get(k) for k in
                                        ("ai_brain", "behavioral_contract", "ui_spec", "permissions"))
    if not isinstance(brain, dict) or not isinstance(brain.get("role"), str) or not brain["role"].strip():
        _stop("CARTRIDGE_BRAIN")
    if not _strings(brain.get("constraints")):
        _stop("CARTRIDGE_BRAIN_CONSTRAINTS")
    if not isinstance(behavior, dict) or not _strings(behavior.get("source_document_ids")) or not _strings(behavior.get("requirements")):
        _stop("CARTRIDGE_BEHAVIOR")
    if not isinstance(permissions, dict) or not _strings(permissions.get("allowed_actions")):
        _stop("CARTRIDGE_PERMISSIONS")
    if permissions.get("external_data") is not False:
        _stop("CARTRIDGE_EXTERNAL_DATA")
    if not isinstance(ui, dict) or not _strings(ui.get("allowed_components"), COMPONENTS):
        _stop("CARTRIDGE_COMPONENTS")
    fields = ui.get("fields")
    if not isinstance(fields, list) or not 1 <= len(fields) <= 20:
        _stop("CARTRIDGE_FIELDS")
    seen = set()
    for field in fields:
        if not isinstance(field, dict) or not _identifier(field.get("id")) or field["id"] in seen:
            _stop("CARTRIDGE_FIELD_ID")
        seen.add(field["id"])
        if field.get("type") not in FIELD_TYPES or not isinstance(field.get("label"), str) or not 0 < len(field["label"]) <= 120:
            _stop("CARTRIDGE_FIELD_TYPE")
        if field.get("required") is not True:
            _stop("CARTRIDGE_FIELD_REQUIRED")
        if field["type"] == "text":
            if not isinstance(field.get("max_length"), int) or isinstance(field["max_length"], bool) or not 1 <= field["max_length"] <= 4000:
                _stop("CARTRIDGE_TEXT_BOUND")
        if field["type"] == "measurement_rows":
            low, high, columns = field.get("min_rows"), field.get("max_rows"), field.get("columns")
            if (not isinstance(low, int) or isinstance(low, bool) or not isinstance(high, int) or
                isinstance(high, bool) or not 1 <= low <= high <= 30 or
                not isinstance(columns, list) or not 1 <= len(columns) <= 12):
                _stop("CARTRIDGE_ROW_BOUND")
            ids = set()
            for col in columns:
                if (not isinstance(col, dict) or not _identifier(col.get("id")) or
                    col["id"] in ids or col.get("type") not in CELL_TYPES or
                    not isinstance(col.get("required"), bool)):
                    _stop("CARTRIDGE_COLUMN")
                ids.add(col["id"])
    action = ui.get("action")
    if not isinstance(action, dict) or not _identifier(action.get("id")):
        _stop("CARTRIDGE_ACTION")
    adapter = action.get("adapter")
    if adapter not in ADAPTERS or adapter != product_id:
        _stop("CARTRIDGE_ADAPTER_SCOPE")
    bindings = action.get("payload_binding")
    if (not isinstance(bindings, dict) or set(bindings) != seen or
        any(bindings[k] != k for k in seen)):
        _stop("CARTRIDGE_BINDING")
    if not _strings(ui.get("result_components"), COMPONENTS):
        _stop("CARTRIDGE_RESULTS")
    if not set(ui["result_components"]).issubset(set(ui["allowed_components"])):
        _stop("CARTRIDGE_RESULTS")
    return artifact
