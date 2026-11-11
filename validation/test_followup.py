"""Bounded AI-directed Apollo follow-up tests. All services simulated."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from apollo_flow import MorpheusFlow, FlowStop

class TestFollowup(unittest.TestCase):
    def setUp(self):
        self.queries = []
        self.ai_calls = []
        def search(product_id, query):
            self.queries.append((product_id, query))
            if product_id == "morpheus_adaptive_ui":
                return {"decision":"PASS","results":[{"product_id":product_id,"document_id":"f93144ea664b494094cee9e1debb2e0f","content":"display_name: Calculator product_id: calculator display_name: Hippocrates Labs product_id: hippocrates_labs"}]}
            followup = len(self.queries) > 2
            return {"decision":"PASS","product_id":product_id,"results":[{"product_id":product_id,"document_id":"ui" if followup else "brain","content":"UI components" if followup else "AI brain"}]}
        def ai(**kw):
            self.ai_calls.append(kw)
            if len(kw["context"]) == 1:
                return {"status":"needs_more_context","search_query":"UI components web parts"}
            return {"status":"preview","ui_parts":[{"type":"table","columns":["Name"],"rows":[]}]}
        self.flow = MorpheusFlow(search, ai)
        self.flow.discover()

    def test_followup(self):
        self.assertEqual(self.flow.ask("calculator","show a table")["status"],"preview")
        self.assertEqual(len(self.queries),3)
        self.assertEqual(len(self.ai_calls[-1]["context"]),2)

    def test_scoped_followup(self):
        self.flow.ask("hippocrates_labs","show labs")
        self.assertEqual([p for p,q in self.queries[1:]],["hippocrates_labs","hippocrates_labs"])

    def test_invalid_query(self):
        self.flow.ai=lambda **kw: {"status":"needs_more_context","search_query":""}
        with self.assertRaisesRegex(FlowStop,"INVALID_FOLLOWUP_QUERY"): self.flow.ask("calculator","show table")

    def test_no_new_context(self):
        original=self.flow.search
        def repeated(product_id,query):
            result=original(product_id,query)
            if product_id=="calculator":
                result["results"][0]["document_id"]="brain"
            return result
        self.flow.search=repeated
        with self.assertRaisesRegex(FlowStop,"NO_NEW_CONTEXT"): self.flow.ask("calculator","show table")

    def test_unsafe_ui(self):
        self.flow.ai=lambda **kw: {"status":"preview","ui_parts":[{"type":"script"}]}
        with self.assertRaisesRegex(FlowStop,"INVALID_UI_PARTS"): self.flow.ask("calculator","show table")

    def test_stop(self):
        self.flow.ai=lambda **kw: {"status":"stop","reason":"not approved"}
        self.assertEqual(self.flow.ask("calculator","show table")["status"],"stop")

if __name__=="__main__": unittest.main(verbosity=2)
