import ast,json,sys,unittest
from unittest.mock import patch
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'calling'))
from input_loaded_fields import own_equipment_affected_units
class Fake:
 def array(self,a,b):return [0x10000,0x20000]
 def require(self,a,name):pass
 def i(self,a):return {0x1001c:1,0x2001c:2}[a]
 def q(self,a):return {0x103b8:0x30000,0x203b8:0x40000}[a]
def row(n,name='infantry_equipment'):return [{'equipment_type':name,'amount_raw':n}]
class Tests(unittest.TestCase):
 def run_reader(self,data):
  with patch('input_loaded_fields._typed_equipment_amounts',side_effect=lambda r,p,*a:data[p]):return own_equipment_affected_units(Fake(),0x90000)
 def data(self):return {0x30120:row(100),0x10348:row(80),0x40120:row(100),0x20348:row(100)}
 def test_physical_shortage_and_full_strength_negative(self):
  out,ev=self.run_reader(self.data());self.assertEqual(out,{'infantry_equipment':[1]});self.assertEqual(ev['incomplete_types_omitted'],[])
 def test_absent_bucket_is_not_zero(self):
  d=self.data();d[0x20348]=[];out,ev=self.run_reader(d);self.assertEqual(out,{});self.assertEqual(ev['incomplete_types_omitted'],['infantry_equipment'])
 def test_other_type_not_promoted(self):
  d={k:row(100 if k in(0x30120,0x40120)else 1,'tank_equipment')for k in self.data()};self.assertEqual(self.run_reader(d)[0],{})
 def test_current_export_has_twenty_not_request_fifteen(self):
  d=json.loads((R/'research/t199_full_capture_fixed_a.json').read_text(encoding='utf-8'));rows=d['observation']['world']['shortages']['equipment'];x=next(x for x in rows if x['equipment_type']=='infantry_equipment');ids=x['affected_unit_ids'];self.assertEqual(len(ids),20);self.assertNotIn(1843,ids);self.assertTrue(set((1831,1832,1833,1834,1841)).issubset(ids));self.assertNotIn('demanded',x);self.assertNotIn('deficit',x);self.assertNotIn('affected_plan_ids',x)
 def test_end_to_end_observation_repeatable(self):
  a=json.loads((R/'research/t199_full_capture_fixed_a.json').read_text(encoding='utf-8'));b=json.loads((R/'research/t199_full_capture_fixed_b.json').read_text(encoding='utf-8'));self.assertEqual(a['observation'],b['observation']);self.assertEqual(a['observation']['meta']['speed'],'pause');self.assertEqual(len(a['observation']['world']['armies']),2);self.assertEqual(len(a['observation']['world']['army_groups']),1)
 def test_full_contract_still_incomplete_not_misrepresented(self):
  d=json.loads((R/'research/t199_full_capture_fixed_a.json').read_text(encoding='utf-8'));self.assertFalse(d['complete_input']);self.assertFalse(d['schema_validation']['valid']);self.assertEqual(d['schema_validation']['error_count'],50);self.assertTrue(all('is a required property'in e['message']for e in d['schema_validation']['errors']))
 def test_no_time_pause_or_execution_change(self):
  d=json.loads((R/'research/t199_e2e_audit.json').read_text(encoding='utf-8'));self.assertEqual(d['before'],d['after']);self.assertEqual(d['before']['pause'],1);self.assertTrue(all(not p['executing']for p in d['after']['plans']));self.assertFalse(d['gate_open']);self.assertEqual(d['game_writes'],0);self.assertEqual(d['post_calls'],0);self.assertEqual(d['remote_calls'],0)
 def test_local_capture_has_no_remote_or_post_calls(self):
  for name in ('input_capture_live.py','input_loaded_fields.py'):
   tree=ast.parse((R/'calling'/name).read_text(encoding='utf-8'))
   calls=[n.func.attr if isinstance(n.func,ast.Attribute)else n.func.id if isinstance(n.func,ast.Name)else ''for n in ast.walk(tree)if isinstance(n,ast.Call)]
   for bad in ('do_post','_remote','WriteProcessMemory','factory_make'):self.assertNotIn(bad,calls)
 def test_inventory_acceptance(self):
  d=json.loads((R/'research/t199_e2e_audit.json').read_text(encoding='utf-8'))['inventory'];self.assertEqual((d['tables'],d['fields'],d['columns'],d['verified'],d['unverified']),(14,116,3,72,44));self.assertEqual(d['sha256'],'4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a')
if __name__=='__main__':unittest.main()
