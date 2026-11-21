import ast,json,struct,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'calling'))
from input_loaded_fields import LoadedReader,unit_supply
from input_observation import ObservationError
from command_receipt import retain_unpaused_risk
class Tests(unittest.TestCase):
 def setup_reader(self,source=100000,capacity=10800000,reserve=7500000,hours=72,threshold=99000,special=0,cls='CArmy'):
  self.army=0x10000;self.base=0x100000;self.mem={self.army:struct.pack('<Q',0x50000),self.army+0x40:struct.pack('<q',source),self.army+0x600:struct.pack('<q',capacity),self.army+0x610:struct.pack('<q',reserve),self.army+0x2f8:struct.pack('<Q',special),self.base+0x33e3678:struct.pack('<i',hours),self.base+0x33e3e00:struct.pack('<q',threshold)}
  return LoadedReader(lambda a,n:self.mem[a][:n],lambda a:'.?AV'+cls+'@@')
 def run_reader(self,**kw):
  r=self.setup_reader(**kw);return unit_supply(r,self.army,self.base)
 def test_full_and_reserve_overflow_clamp(self):
  d,e=self.run_reader();self.assertEqual(d,{'ratio':1.0,'in_supply':True});self.assertTrue(e['isolated_omitted'])
 def test_live_depleted_positive(self):self.assertEqual(self.run_reader(source=61285,reserve=6415676)[0],{'ratio':0.89106,'in_supply':False})
 def test_live_mild_shortage_positive(self):self.assertEqual(self.run_reader(source=91240,reserve=7022610)[0],{'ratio':0.97536,'in_supply':False})
 def test_threshold_boundary(self):
  self.assertTrue(self.run_reader(source=99000,reserve=0)[0]['in_supply']);self.assertFalse(self.run_reader(source=98999,reserve=0)[0]['in_supply'])
 def test_official_special_branch(self):self.assertEqual(self.run_reader(source=0,reserve=0,special=0x80000)[0],{'ratio':0.0,'in_supply':True})
 def test_no_capacity_branch(self):self.assertEqual(self.run_reader(capacity=0)[0],{'ratio':0.0,'in_supply':False})
 def test_invalid_divisor_rejected(self):
  with self.assertRaises(ObservationError):self.run_reader(hours=0)
 def test_invalid_threshold_rejected(self):
  with self.assertRaises(ObservationError):self.run_reader(threshold=100001)
 def test_sentinel_and_overflow_rejected(self):
  for n in(-1,2**63-1):
   with self.assertRaises(ObservationError):self.run_reader(reserve=n)
 def test_wrong_object_identity_rejected(self):
  with self.assertRaises(ObservationError):self.run_reader(cls='CProvince')
 def test_new_dependencies_tracked(self):
  r=self.setup_reader();unit_supply(r,self.army,self.base);self.mem[self.army+0x610]=struct.pack('<q',7000000)
  with self.assertRaises(ObservationError):r.stable()
 def test_real_live_inputs_not_default_only(self):
  d=json.loads((R/'research/t201_supply_ui_live_inputs.json').read_text(encoding='utf-8'));u=d['units'];self.assertEqual((d['buffer_parameter_raw'],d['threshold_raw']),(72,99000));self.assertEqual(sum(x['ui_out_of_supply_candidate']for x in u),9);self.assertEqual(sum(not x['ui_out_of_supply_candidate']for x in u),12)
  for x in u:self.assertEqual(self.run_reader(source=x['consumer_factor_30_raw'],capacity=x['army_600_raw'],reserve=x['army_610_raw'])[0]['ratio'],x['ui_ratio_candidate_raw']/100000)
 def test_pause_failure_risk_not_cleared(self):
  self.assertTrue(retain_unpaused_risk(was_unpaused=True,observed_pause=0));self.assertTrue(retain_unpaused_risk(was_unpaused=True,observed_pause=None));self.assertFalse(retain_unpaused_risk(was_unpaused=True,observed_pause=1))
 def test_historical_writer_fenced_without_execution(self):
  text=(R/'research/_t198_order_sample.py').read_text(encoding='utf-8');tree=ast.parse(text);self.assertIsInstance(tree.body[0],ast.Raise);self.assertEqual(text.count('unpaused=False'),1);self.assertIn('unpaused=retain_unpaused_risk(',text)
  handlers=[n for n in ast.walk(tree)if isinstance(n,ast.ExceptHandler)];calls=[n.func.attr for h in handlers for n in ast.walk(h)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)];self.assertNotIn('do_post',calls)
 def test_borderwar_not_ordinary_combat_start(self):
  d=json.loads((R/'research/t201_plan_combat_owners.json').read_text(encoding='utf-8'));self.assertEqual(d['0x1489550'][0]['class'],'.?AVCLandBorderWarCombat@@');self.assertEqual(d['0x1347fd0'][0]['class'],'.?AVCLandCombat@@')
 def test_end_to_end_supply_export(self):
  a=json.loads((R/'research/t201_full_capture_a.json').read_text(encoding='utf-8'));b=json.loads((R/'research/t201_full_capture_b.json').read_text(encoding='utf-8'));self.assertEqual(a['observation'],b['observation']);units=a['observation']['world']['own_units'];self.assertEqual(sum(not u['supply']['in_supply']for u in units),9);self.assertEqual(len(units),21);self.assertTrue(all('isolated'not in u['supply']for u in units));self.assertFalse(a['complete_input']);self.assertFalse(a['schema_validation']['valid']);self.assertTrue(all('is a required property'in e['message']for e in a['schema_validation']['errors']))
if __name__=='__main__':unittest.main()
