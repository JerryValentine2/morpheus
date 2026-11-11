import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from apollo_flow import MorpheusFlow,FlowStop
REGISTRY='''# Morpheus Product Selector Registry — V1 Authority: Apollo Status: CANDIDATE_DISCOVERABLE — NOT APPROVED FOR RUNTIME ACTIVATION Purpose: Provide user-friendly dropdown labels mapped to exact Apollo product IDs. This is a registry document within the Morpheus Apollo product scope, not a GitHub registry. products: - display_name: Calculator product_id: calculator cartridge_document_id: 291c70cec4d941a59406da5fd7dca63b approved: false activation_enabled: false - display_name: Hippocrates Labs product_id: hippocrates_labs cartridge_document_id: 7cbef5aab9304d42a75b3ca7d5264afc approved: false activation_enabled: false Dropdown shows display_name and submits product_id.'''
CALC='AI brain interprets arbitrary math questions. UI: text input, action button, result text. No hardcoded enum.'
LAB='AI brain interprets natural-language lab questions. UI: lab request input, table, optional chart, status text. Synthetic WBC 7.2.'
class Adapter:
 def __init__(self):self.calls=[];self.fail=None
 def __call__(self,product_id,query):
  self.calls.append(product_id)
  if self.fail==product_id:return {'decision':'STOP','results':[]}
  if product_id=='morpheus_adaptive_ui':return {'decision':'PASS','results':[{'product_id':product_id,'document_id':'f93144ea664b494094cee9e1debb2e0f','content':REGISTRY}]}
  if product_id in ('calculator','hippocrates_labs'):
   return {'decision':'PASS','results':[{'product_id':product_id,'document_id':'real-apollo-source','content':CALC if product_id=='calculator' else LAB}]}
  raise ValueError(product_id)
def agent(**kw):
 assert kw['context'] and kw['product_id'] in ('calculator','hippocrates_labs')
 if kw['product_id']=='calculator':return {'status':'preview','ui_parts':[{'type':'input','label':'Calculation'},{'type':'text','content':'15% of 200 = 30 (simulated AI)'}]}
 return {'status':'preview','ui_parts':[{'type':'table','columns':['Measurement','Value','Units'],'rows':[['WBC','7.2','10^3/uL']]},{'type':'chart','label':'Synthetic lab chart'}]}
class Tests(unittest.TestCase):
 def setUp(self):self.a=Adapter();self.f=MorpheusFlow(self.a,agent)
 def test_discover(self):self.assertEqual(self.f.discover(),[{'label':'Calculator','value':'calculator'},{'label':'Hippocrates Labs','value':'hippocrates_labs'}])
 def test_calculator(self):self.f.discover();self.assertEqual(self.f.ask('calculator','15% of 200')['status'],'preview');self.assertEqual(self.a.calls,['morpheus_adaptive_ui','calculator'])
 def test_labs(self):self.f.discover();self.assertEqual(self.f.ask('hippocrates_labs','show WBC')['ui_parts'][0]['type'],'table')
 def test_switch(self):self.f.discover();self.f.ask('calculator','15% of 200');self.f.ask('hippocrates_labs','show WBC');self.assertEqual(self.a.calls,['morpheus_adaptive_ui','calculator','hippocrates_labs'])
 def test_unknown_product(self):self.f.discover();self.assertRaisesRegex(FlowStop,'UNKNOWN_PRODUCT',self.f.ask,'calendar_ms','hello')
 def test_empty(self):self.f.discover();self.assertRaisesRegex(FlowStop,'EMPTY_MESSAGE',self.f.ask,'calculator','')
 def test_apollo_failure(self):self.f.discover();self.a.fail='calculator';self.assertRaisesRegex(FlowStop,'APOLLO_PRODUCT_SEARCH_FAILED',self.f.ask,'calculator','hello')
 def test_invalid_ui(self):self.f.discover();self.f.ai=lambda **kw:{'status':'preview','ui_parts':[{'type':'script'}]};self.assertRaisesRegex(FlowStop,'INVALID_UI_PARTS',self.f.ask,'calculator','hello')
 def test_registry_failure(self):self.a.fail='morpheus_adaptive_ui';self.assertRaisesRegex(FlowStop,'APOLLO_DISCOVERY_FAILED',self.f.discover)
 def test_duplicate_registry(self):
  global REGISTRY
  old=REGISTRY
  try:
   REGISTRY=old+' - display_name: Duplicate product_id: calculator cartridge_document_id: abc'
   self.assertRaisesRegex(FlowStop,'INVALID_REGISTRY',self.f.discover)
  finally:REGISTRY=old
if __name__=='__main__':unittest.main(verbosity=2)
