import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from ui_validation import validate_ui_parts, UIValidationError

class UITests(unittest.TestCase):
    def reject(self, parts):
        with self.assertRaises(UIValidationError):
            validate_ui_parts(parts)

    def test_text(self): self.assertEqual(validate_ui_parts([{"type":"text","content":"ok"}])[0]["content"], "ok")
    def test_table(self): validate_ui_parts([{"type":"table","columns":["x"],"rows":[["ok"],[1],[1.5]]}])
    def test_input(self): validate_ui_parts([{"type":"input","label":"Prompt"}])
    def test_action(self): validate_ui_parts([{"type":"action","label":"Calculate"}])
    def test_chart(self): validate_ui_parts([{"type":"chart","label":"Trend"}])
    def test_script_rejected(self): self.reject([{"type":"script","src":"evil"}])
    def test_html_field_rejected(self): self.reject([{"type":"text","content":"ok","html":"<script>x</script>"}])
    def test_missing_label(self): self.reject([{"type":"action"}])
    def test_wrong_cell_type(self): self.reject([{"type":"table","columns":["x"],"rows":[[{}]]}])
    def test_wrong_row_width(self): self.reject([{"type":"table","columns":["x"],"rows":[["x","y"]]}])
    def test_nonfinite(self): self.reject([{"type":"table","columns":["x"],"rows":[[float("nan")]]}])
    def test_many_parts(self): self.reject([{"type":"text","content":"ok"}]*31)
    def test_empty(self): self.reject([])
    def test_long_text(self): self.reject([{"type":"text","content":"x"*2001}])
    def test_many_rows(self): self.reject([{"type":"table","columns":["x"],"rows":[["x"]]*101}])
    def test_boolean_cell(self): self.reject([{"type":"table","columns":["x"],"rows":[[True]]}])

if __name__ == "__main__":
    unittest.main(verbosity=2)
