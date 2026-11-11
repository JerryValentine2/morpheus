"""Strict, renderer-aligned validation for untrusted AI UI proposals."""
import math

class UIValidationError(ValueError):
    pass

def _text(value, name, limit=2000):
    if not isinstance(value, str) or len(value) > limit:
        raise UIValidationError(name)
    return value

def validate_ui_parts(parts):
    if not isinstance(parts, list) or not 1 <= len(parts) <= 30:
        raise UIValidationError("PARTS_COUNT")
    validated = []
    for part in parts:
        if not isinstance(part, dict):
            raise UIValidationError("PART_NOT_OBJECT")
        kind = part.get("type")
        fields = {
            "text": {"type", "content"},
            "input": {"type", "label"},
            "action": {"type", "label"},
            "table": {"type", "columns", "rows"},
            "chart": {"type", "label"},
        }
        if kind not in fields or set(part) != fields[kind]:
            raise UIValidationError("PART_SCHEMA")
        if kind == "text":
            _text(part["content"], "TEXT_CONTENT")
        elif kind in ("input", "action", "chart"):
            _text(part["label"], "LABEL", 120)
        elif kind == "table":
            cols, rows = part["columns"], part["rows"]
            if not isinstance(cols, list) or not 1 <= len(cols) <= 12 or not all(isinstance(c, str) and len(c) <= 120 for c in cols):
                raise UIValidationError("TABLE_COLUMNS")
            if not isinstance(rows, list) or len(rows) > 100:
                raise UIValidationError("TABLE_ROWS")
            for row in rows:
                if not isinstance(row, list) or len(row) != len(cols):
                    raise UIValidationError("TABLE_ROW_WIDTH")
                for value in row:
                    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                        raise UIValidationError("TABLE_CELL_TYPE")
                    if isinstance(value, float) and not math.isfinite(value):
                        raise UIValidationError("TABLE_NONFINITE")
                    if len(str(value)) > 500:
                        raise UIValidationError("TABLE_CELL_LENGTH")
        validated.append(part)
    return validated
