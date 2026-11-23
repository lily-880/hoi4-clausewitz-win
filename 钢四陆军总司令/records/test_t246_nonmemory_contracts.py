"""Offline schema-structure checks only: no runtime config, ledger, process or game calls."""
import os,json,hashlib,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
C=json.loads((HERE/'t246_nonmemory_contracts.json').read_text(encoding='utf-8'))
REPO_SCHEMA=Path(__file__).resolve().parents[2]/'calling/tables/generalissimo_input.schema.json'
SCHEMA=Path(os.environ.get('HOI4_RESEARCH_SCHEMA',str(REPO_SCHEMA if REPO_SCHEMA.is_file() else C['schema_source_box'])))
RAW=SCHEMA.read_bytes()
if hashlib.sha256(RAW).hexdigest()!=C['schema_sha256']:raise RuntimeError('Exact historical source schema pin required; do not bless changed bytes')
J=json.loads(RAW)
def resolve(x):
 if '$ref' not in x:return x
 y=J
 for k in x['$ref'][2:].split('/'):y=y[k]
 return y
def extract(path):
 x=J;chain=[]
 for part in path.split('.'):
  x=resolve(x)
  if x.get('type')=='array':x=resolve(x['items'])
  chain.append({'member':part,'required_in_parent':part in x.get('required',[])})
  x=x['properties'][part]
 return resolve(x),chain
class NonmemoryContractChecks(unittest.TestCase):
 def test_12_fragment_source_identity_and_required_paths(self):
  self.assertEqual(len(C['fields']),12)
  for path,f in C['fields'].items():
   node,chain=extract(path);self.assertEqual(node,f['contract']);self.assertEqual(chain,f['required_chain'])
  self.assertEqual(sum(x['field_itself_required'] for x in C['fields'].values()),6)
 def test_config_is_boolean_and_explicit_scope_shapes_not_runtime_defaults(self):
  a,_=extract('meta.allow_write');self.assertEqual(a,{'type':'boolean'})
  g,_=extract('meta.geography_scope');v=g['anyOf'];self.assertEqual(v[0],{'type':'null'});self.assertEqual(v[1]['required'],['kind']);self.assertEqual(v[1]['properties']['kind']['enum'],['global']);self.assertEqual(v[2]['required'],['kind','province_ids']);self.assertEqual(v[2]['properties']['kind']['enum'],['theater']);self.assertNotIn('default',g)
 def test_policy_optional_members_and_five_named_stances(self):
  p=resolve(J['properties']['policy']);self.assertIn('policy',J['required']);self.assertEqual(p['required'],[]);self.assertFalse(p['additionalProperties']);self.assertEqual(p['properties']['instructions'],{'type':'string'});self.assertEqual(p['properties']['stance']['enum'],['preserve_force','hold_line','annihilate','economize_manpower','custom'])
 def test_receipt_required_four_and_optional_not_nullable(self):
  f=J['$defs']['Feedback'];self.assertEqual(f['required'],['last_orders']);a=f['properties']['last_orders'];self.assertEqual(a['items']['required'],['order_seq','type','subject_ids','accepted']);self.assertNotIn('minItems',a);props=a['items']['properties'];self.assertEqual(props['plan_id'],{'type':'integer'});self.assertEqual(props['error'],{'type':'string'});self.assertEqual(props['target_province_ids'],{'type':'array','items':{'type':'integer'}});self.assertEqual(f['properties']['ticks_since_issue'],{'type':'integer'})
 def test_schema_does_not_supply_ledger_bounds_or_defaults(self):
  for f in C['fields'].values():self.assertNotIn('default',f['contract'])
  for path in ['feedback.last_orders.order_seq','feedback.ticks_since_issue']:
   n,_=extract(path);self.assertNotIn('minimum',n);self.assertNotIn('maximum',n)
  for path in ['feedback.last_orders.subject_ids','feedback.last_orders.target_province_ids']:
   n,_=extract(path);self.assertNotIn('minItems',n);self.assertNotIn('uniqueItems',n);self.assertNotIn('minimum',n['items'])
 def test_order_name_union_is_not_native_abi_certificate(self):
  n,_=extract('feedback.last_orders.type');base=resolve(n['anyOf'][0])['enum'];extra=n['anyOf'][1]['enum'];self.assertIn('retreat',base);self.assertIn('unknown',base);self.assertIn('create_frontline',extra);self.assertIn('train',extra);self.assertEqual(set(n),{'anyOf'});self.assertEqual(C['promotions'],[])
if __name__=='__main__':unittest.main(verbosity=2)
