"""End-to-end Flask request tests for simulated AI-directed Apollo retrieval.
Run from repository root: python -m unittest discover -s validation -p test_api_followup.py -v
"""
import unittest
from api import create_app

class FollowupApiTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.reason_calls = []
        def search(product_id, query):
            self.calls.append((product_id, query))
            if product_id == "morpheus_adaptive_ui":
                return {"decision":"PASS","product_id":product_id,"results":[{
                    "product_id":product_id,
                    "document_id":"f93144ea664b494094cee9e1debb2e0f",
                    "content":"display_name: Calculator product_id: calculator\ndisplay_name: Hippocrates Labs product_id: hippocrates_labs"}]}
            doc = "ui" if query.startswith("UI components") else "brain"
            return {"decision":"PASS","product_id":product_id,"results":[{
                "product_id":product_id,"document_id":doc,"content":doc+" contract"}]}
        def ai(**kw):
            self.reason_calls.append(kw)
            if len(kw["context"]) == 1:
                return {"status":"needs_more_context","search_query":"UI components for current product"}
            return {"status":"preview","ui_parts":[{"type":"text","content":"Simulated interface"}]}
        self.client = create_app(search=search, ai=ai).test_client()

    def test_calculator_full_sequence(self):
        response = self.client.post("/api/preview", json={"product_id":"calculator","message":"Show result"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json["result"]["status"],"preview")
        self.assertEqual(len(self.reason_calls),2)
        self.assertEqual([p for p,_ in self.calls],["morpheus_adaptive_ui","calculator","calculator"])

    def test_hippocrates_full_sequence(self):
        response = self.client.post("/api/preview", json={"product_id":"hippocrates_labs","message":"Show synthetic labs"})
        self.assertEqual(response.status_code,200)
        self.assertEqual([p for p,_ in self.calls],["morpheus_adaptive_ui","hippocrates_labs","hippocrates_labs"])

    def test_reject_unknown_product(self):
        response = self.client.post("/api/preview",json={"product_id":"unknown","message":"Hi"})
        self.assertEqual(response.status_code,422)
        self.assertEqual(len(self.reason_calls),0)

    def test_no_cross_product_retrieval(self):
        self.client.post("/api/preview",json={"product_id":"calculator","message":"Hi"})
        self.client.post("/api/preview",json={"product_id":"hippocrates_labs","message":"Hi"})
        self.assertEqual([p for p,_ in self.calls],[
            "morpheus_adaptive_ui","calculator","calculator",
            "morpheus_adaptive_ui","hippocrates_labs","hippocrates_labs"])

    def test_no_activation(self):
        response=self.client.post("/api/preview",json={"product_id":"calculator","message":"Hi"})
        self.assertFalse(response.json["activation_enabled"])
        self.assertEqual(response.json["mode"],"SIMULATED")

if __name__=="__main__": unittest.main(verbosity=2)
