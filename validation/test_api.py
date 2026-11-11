import unittest
from api import create_app

class MorpheusApiTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["mode"], "SIMULATED")
        self.assertFalse(r.json["production_activation"])

    def test_frontend(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Adaptive product interface", r.data)

    def test_discovery(self):
        r = self.client.get("/api/products")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["products"], [
            {"label": "Calculator", "value": "calculator"},
            {"label": "Hippocrates Labs", "value": "hippocrates_labs"}
        ])

    def test_calculator_preview(self):
        r = self.client.post("/api/preview", json={"product_id": "calculator", "message": "15% of 200"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["result"]["status"], "preview")
        self.assertEqual(r.json["mode"], "SIMULATED")

    def test_labs_preview(self):
        r = self.client.post("/api/preview", json={"product_id": "hippocrates_labs", "message": "show synthetic WBC"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["result"]["ui_parts"][-1]["type"], "table")

    def test_switch_isolation(self):
        self.client.post("/api/preview", json={"product_id": "calculator", "message": "math"})
        r = self.client.post("/api/preview", json={"product_id": "hippocrates_labs", "message": "WBC"})
        self.assertTrue(all("Calculator" not in str(p) for p in r.json["result"]["ui_parts"]))

    def test_unknown_product(self):
        r = self.client.post("/api/preview", json={"product_id": "unlisted", "message": "hi"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json["error"], "UNKNOWN_PRODUCT")

    def test_empty_message(self):
        r = self.client.post("/api/preview", json={"product_id": "calculator", "message": ""})
        self.assertEqual(r.status_code, 422)

    def test_invalid_json(self):
        r = self.client.post("/api/preview", data="not-json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_no_activation(self):
        r = self.client.get("/api/products")
        self.assertFalse(r.json["activation_enabled"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
