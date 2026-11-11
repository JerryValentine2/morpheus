"""Offline unit tests; connector and model are injected fakes, not live runtime."""
import unittest
from runtime.apollo_flow import MorpheusFlow, FlowStop
def search(product_id,query):
    return {"decision":"PASS","results":[{"product_id":product_id,"document_id":"doc-"+product_id,"content":"AI brain and UI parts"}]}
def ai(**kw): return {"status":"preview","ui_parts":[{"type":"text","content":"Preview only"}]}
class Registry:
    def list_products(self):
        from types import SimpleNamespace
        return [SimpleNamespace(product_id="calculator",display_name="Calculator"),SimpleNamespace(product_id="hippocrates_labs",display_name="Hippocrates Labs")]
class Tests(unittest.TestCase):
    def setUp(self): self.f=MorpheusFlow(search,ai,registry=Registry())
    def test_missing_registry_fails_closed(self):
        with self.assertRaisesRegex(FlowStop,"NOT_CONFIGURED"):
            MorpheusFlow(search,ai).discover()
    def test_discovery(self): self.assertEqual([x["value"] for x in self.f.discover()],["calculator","hippocrates_labs"])
    def test_ask(self): self.f.discover(); self.assertEqual(self.f.ask("calculator","15% of 200")["status"],"preview")
    def test_bad_product(self): self.f.discover(); self.assertRaises(FlowStop,self.f.ask,"other","hello")
    def test_no_discovery(self): self.assertRaises(FlowStop,self.f.ask,"calculator","hello")
    def test_unsafe_ui(self):
        self.f.discover(); self.f.ai=lambda **kw:{"status":"preview","ui_parts":[{"type":"script"}]}
        self.assertRaises(FlowStop,self.f.ask,"calculator","hello")
if __name__=="__main__": unittest.main()
