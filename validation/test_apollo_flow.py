"""Offline unit tests; connector and model are injected fakes, not live runtime."""
import unittest
from runtime.apollo_flow import MorpheusFlow, FlowStop
REGISTRY="products: - display_name: Calculator product_id: calculator cartridge_document_id: abc - display_name: Hippocrates Labs product_id: hippocrates_labs cartridge_document_id: def"
def search(product_id,query):
    if product_id=="morpheus_adaptive_ui":
        return {"decision":"PASS","results":[{"product_id":product_id,"document_id":"f93144ea664b494094cee9e1debb2e0f","content":REGISTRY}]}
    return {"decision":"PASS","results":[{"product_id":product_id,"document_id":"doc-"+product_id,"content":"AI brain and UI parts"}]}
def ai(**kw): return {"status":"preview","ui_parts":[{"type":"text","content":"Preview only"}]}
class Tests(unittest.TestCase):
    def setUp(self): self.f=MorpheusFlow(search,ai)
    def test_discovery(self): self.assertEqual([x["value"] for x in self.f.discover()],["calculator","hippocrates_labs"])
    def test_ask(self): self.f.discover(); self.assertEqual(self.f.ask("calculator","15% of 200")["status"],"preview")
    def test_bad_product(self): self.f.discover(); self.assertRaises(FlowStop,self.f.ask,"other","hello")
    def test_no_discovery(self): self.assertRaises(FlowStop,self.f.ask,"calculator","hello")
    def test_unsafe_ui(self):
        self.f.discover(); self.f.ai=lambda **kw:{"status":"preview","ui_parts":[{"type":"script"}]}
        self.assertRaises(FlowStop,self.f.ask,"calculator","hello")
if __name__=="__main__": unittest.main()
