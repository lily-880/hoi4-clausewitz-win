import unittest,json,struct,ast
from pathlib import Path
import t226_frozen_adjudication as m
Q=Path(__file__).parent
class AdjudicationTests(unittest.TestCase):
 def setUp(self):self.d={p.name:json.loads(p.read_text()) for p in Q.glob('t226_*.json')}
 def bad(self):
  with self.assertRaises(m.Unproved):m.replay(self.d)
 def test_01_live_full_manning_is_not_missing(self):
  r=m.replay(self.d);self.assertEqual(r['per_unit_controls'][0],{'unit_id':500,'current':7300,'full_requirement':7300,'missing':0})
 def test_02_eight_of49_not_national_zero(self):
  r=m.replay(self.d);self.assertEqual(len(r['per_unit_controls']),8);self.assertFalse(r['sample_is_national_census']);self.assertNotIn('national_needed',r)
 def test_03_summed_perunit_substitution_forbidden(self):
  with self.assertRaises(m.Unproved):m.export_national_needed(sum(x['engine_need_total'] for x in self.d[m.LIVE]['rows']))
 def test_04_national_usage_not_needed(self):self.d['t226_national_getter_classification.json']['ui_argument_names'][0]['text']='NATIONAL_REINFORCEMENT_NEEDED';self.bad()
 def test_05_perunit_delivery_cap_not_national(self):self.d[m.LIVE]['national_needed_proved']=True;self.bad()
 def test_06_live_named_threshold_values(self):self.assertEqual(m.replay(self.d)['native_supply_thresholds'],{'ALERT_LOW_SUPPLY_LEVEL':50000,'ALERT_VERY_LOW_SUPPLY_LEVEL':20000})
 def test_07_native_boundary_verylow(self):self.assertEqual((m.native_bucket(19999),m.native_bucket(20000)),(0,1))
 def test_08_native_boundary_low(self):self.assertEqual((m.native_bucket(49999),m.native_bucket(50000)),(1,2))
 def test_09_native_signed_behavior_not_schema_acceptance(self):
  self.assertEqual(m.native_bucket(-1),0)
  with self.assertRaises(m.Unproved):m.qualified_bucket(-1)
 def test_10_observed_bucket_has_no_severity_mapping(self):
  with self.assertRaises(m.Unproved):m.export_crisis(m.qualified_bucket(0))
 def test_11_reversed_thresholds_rejected(self):
  with self.assertRaises(m.Unproved):m.native_bucket(30000,10000,20000)
 def test_12_name_leaf_not_numeric_value(self):self.d[m.BIND]['cells'][0]['value_rva']='0x7924a0';self.bad()
 def test_13_actual_vtable_has_only_two_slots(self):self.d[m.BIND]['cells'][0]['vtable_actual_slot_count']=6;self.bad()
 def test_14_actual_name_key_required(self):self.d[m.BIND]['cells'][0]['name']='ALERT_FAKE';self.bad()
 def test_15_threshold_claim_must_match_raw(self):self.d[m.BIND]['cells'][0]['value']=99999;self.bad()
 def test_16_names_and_config_are_not_alert_positive(self):self.d[m.BIND]['actual_supply_alert_positive_samples']=1;self.bad()
 def test_17_native_leaf_closure_required(self):self.d['t226_supply_alert_threshold_leaf.json']['functions']['0x16d8d50']['unresolved_edges']=[{'reason':'outside'}];self.bad()
 def test_18_full_requirement_cannot_be_relabelled_missing(self):self.d[m.LIVE]['rows'][0]['engine_missing_formula']=7300;self.bad()
 def test_19_shared_fresh_session(self):self.d[m.LIVE]['after']['hour_tick']+=1;self.bad()
 def test_20_shared_type51_gate(self):self.d[m.LIVE]['rows'][0]['handle_type']=4713;self.bad()
 def test_21_shared_code_integrity(self):
  f=self.d['t226_supply_alert_threshold_leaf.json']['functions']['0x16d8d50'];f['raw_hex']='00'+f['raw_hex'][2:];self.bad()
 def test_22_shared_no_live_backend(self):
  tree=ast.parse((Q/'t226_frozen_adjudication.py').read_text());self.assertEqual([n.name for x in ast.walk(tree) if isinstance(x,(ast.Import,ast.ImportFrom)) for n in x.names],['hashlib','struct'])
 def test_23_shared_no_promotions_contract(self):
  r=m.replay(self.d);self.assertEqual(r['promoted_fields'],[]);self.assertFalse(r['complete_input']);self.assertFalse(r['national_needed_exported']);self.assertFalse(r['crisis_exported'])
