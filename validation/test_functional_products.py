"""Functional product acceptance tests: actual computations and supplied-range interpretation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from product_execution import calculator, hippocrates_labs, ProductExecutionError, execute

class FunctionalProducts(unittest.TestCase):
    def test_calculator_real_arithmetic(self):
        self.assertEqual(calculator("(12 + 8) / 4")["result"], 5)
        self.assertEqual(calculator("2 ** 8")["result"], 256)
        self.assertEqual(calculator("7 / 2")["result"], 3.5)
        self.assertEqual(calculator("-5 + 2")["result"], -3)
    def test_calculator_rejects_unsafe_and_invalid(self):
        for expr in ("1/0", "__import__('os')", "2**1000", "1e309", ""):
            with self.subTest(expr=expr), self.assertRaises(ProductExecutionError):
                calculator(expr)
    def test_labs_actual_user_values(self):
        rows = [{"name":"WBC","value":12.0,"unit":"10^3/uL","low":4.0,"high":11.0},
                {"name":"Hemoglobin","value":14.2,"unit":"g/dL","low":12.0,"high":16.0},
                {"name":"Platelets","value":100,"unit":"10^3/uL","low":150,"high":400}]
        result = hippocrates_labs(rows)
        self.assertEqual([r[-1] for r in result["measurements"]],
                         ["above supplied range","within supplied range","below supplied range"])
        self.assertEqual(len(result["ui_parts"][1]["rows"]), 3)
    def test_labs_invalid_range_and_missing_data(self):
        for rows in ([], [{"name":"WBC","value":4,"low":8,"high":2}],
                     [{"name":"WBC","value":float("nan"),"low":2,"high":8}],
                     [{"name":"WBC","value":4,"low":2}]):
            with self.subTest(rows=rows), self.assertRaises(ProductExecutionError):
                hippocrates_labs(rows)
    def test_both_products_dispatch(self):
        self.assertEqual(execute("calculator",{"expression":"6*7"})["result"],42)
        self.assertEqual(execute("hippocrates_labs",{"measurements":[{"name":"X","value":1,"low":0,"high":2}]})["measurements"][0][-1],"within supplied range")
        with self.assertRaises(ProductExecutionError):
            execute("unknown",{})

if __name__ == "__main__":
    unittest.main()
