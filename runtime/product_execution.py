"""Real deterministic domain operations for both Morpheus V1 products.

No synthetic results, eval, LLM claims, diagnoses, or external medical ranges.
These operations are functional building blocks, not completed Apollo AI cartridges.
"""
import ast
import math
import operator
import re

class ProductExecutionError(ValueError):
    pass

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

def _evaluate(node, depth=0):
    if depth > 16:
        raise ProductExecutionError("EXPRESSION_TOO_COMPLEX")
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        if abs(node.value) > 1e12:
            raise ProductExecutionError("NUMBER_OUT_OF_RANGE")
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand, depth+1))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        a = _evaluate(node.left, depth+1)
        b = _evaluate(node.right, depth+1)
        if isinstance(node.op, ast.Pow) and (abs(b) > 12 or abs(a) > 1e6):
            raise ProductExecutionError("POWER_OUT_OF_RANGE")
        try:
            result = _BIN[type(node.op)](a, b)
        except (ZeroDivisionError, OverflowError) as exc:
            raise ProductExecutionError("INVALID_ARITHMETIC") from exc
        if not isinstance(result, (int, float)) or not math.isfinite(result) or abs(result) > 1e15:
            raise ProductExecutionError("RESULT_OUT_OF_RANGE")
        return result
    raise ProductExecutionError("UNSUPPORTED_EXPRESSION")

def calculator(expression):
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 200:
        raise ProductExecutionError("INVALID_EXPRESSION")
    if not re.fullmatch(r"[0-9.()+*/%\s-]+", expression):
        raise ProductExecutionError("UNSUPPORTED_EXPRESSION")
    try:
        value = _evaluate(ast.parse(expression, mode="eval").body)
    except (SyntaxError, RecursionError) as exc:
        raise ProductExecutionError("INVALID_EXPRESSION") from exc
    if not math.isfinite(value):
        raise ProductExecutionError("RESULT_OUT_OF_RANGE")
    return {"product_id": "calculator", "expression": expression, "result": value,
            "ui_parts": [{"type": "text", "content": f"{expression} = {value:g}"}]}

def hippocrates_labs(measurements):
    """Classify provided numbers against provided ranges; never infer clinical norms."""
    if not isinstance(measurements, list) or not 1 <= len(measurements) <= 30:
        raise ProductExecutionError("INVALID_MEASUREMENTS")
    rows = []
    for item in measurements:
        if not isinstance(item, dict):
            raise ProductExecutionError("INVALID_MEASUREMENT")
        name, unit = item.get("name"), item.get("unit", "")
        value, low, high = item.get("value"), item.get("low"), item.get("high")
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ProductExecutionError("INVALID_MEASUREMENT_NAME")
        if not isinstance(unit, str) or len(unit) > 40:
            raise ProductExecutionError("INVALID_UNIT")
        if any(type(n) not in (int, float) or not math.isfinite(n) for n in (value, low, high)):
            raise ProductExecutionError("INVALID_MEASUREMENT_VALUE")
        if low > high:
            raise ProductExecutionError("INVALID_REFERENCE_RANGE")
        flag = "below supplied range" if value < low else "above supplied range" if value > high else "within supplied range"
        rows.append([name.strip(), value, unit, low, high, flag])
    return {"product_id": "hippocrates_labs", "measurements": rows,
            "disclaimer": "Compares user-entered results to user-entered reference ranges only. Not a diagnosis or medical advice.",
            "ui_parts": [{"type": "text", "content": "Results compared with the reference ranges you supplied. Not a diagnosis."},
                         {"type": "table", "columns": ["Test", "Value", "Unit", "Range low", "Range high", "Comparison"], "rows": rows}]}

def execute(product_id, payload):
    if not isinstance(payload, dict):
        raise ProductExecutionError("INVALID_REQUEST")
    if product_id == "calculator":
        return calculator(payload.get("expression"))
    if product_id == "hippocrates_labs":
        return hippocrates_labs(payload.get("measurements"))
    raise ProductExecutionError("UNKNOWN_PRODUCT")
