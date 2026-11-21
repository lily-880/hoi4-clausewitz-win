import unittest,json,ast,struct
from pathlib import Path
import t225_captured_diplomacy_replay as m
Q=Path(__file__).parent
class DiplomacyTests(unittest.TestCase):
 def setUp(self):self.d={p.name:json.loads(p.read_text()) for p in Q.glob('t225_*.json')}
 def bad(self):
  with self.assertRaises(m.Unproved):m.replay(self.d)
 def test_01_actual_bilateral_enemy(self):
  r=m.replay(self.d);self.assertEqual([(p['source_tag'],p['target_tag'],p['candidate_only']) for p in r['pairs'][:2]],[(3,443,'enemy'),(443,3,'enemy')])
 def test_02_actual_foreign_nonwar_not_ally(self):
  self.assertEqual([p['candidate_only'] for p in m.replay(self.d)['pairs'][2:6]],['unknown']*4)
 def test_03_actual_self_separate_from_friendly_foreign(self):self.assertEqual(m.replay(self.d)['pairs'][6]['candidate_only'],'self')
 def test_04_synthetic_nonzero49_is_not_active_war(self):self.assertFalse(m.at_war(123,1))
 def test_05_synthetic_absent_war_never_ally(self):self.assertEqual(m.candidate(m.at_war(0,None)),'unknown')
 def test_06_null_factions_are_not_equal_membership(self):self.assertFalse(m.same_faction(0,0))
 def test_07_synthetic_matching_nonnull_is_faction_only(self):self.assertTrue(m.same_faction(123,123));self.assertFalse(m.replay(self.d)['promotion_eligible'])
 def test_08_no_actual_friendly_no_promotion(self):
  with self.assertRaises(m.Unproved):m.require_promotion(m.replay(self.d))
 def test_09_named_literal_mandatory(self):self.d[m.BIND]['bindings'][0]['literal']='CWarRelation';self.bad()
 def test_10_raw_vtable_eval_link_mandatory(self):
  d=self.d[m.BIND];a=m.BASE+0x280bbe0;row=next(r for r in d['raw_dependencies'] if int(r['address'],16)==a and r['size']==192);b=bytearray.fromhex(row['hex']);struct.pack_into('<Q',b,0xb0,m.BASE+0x3f90f0);row['hex']=b.hex();self.bad()
 def test_11_tooltip_record_binding_mandatory(self):self.d['t225_named_trigger_vtables.json']['rows'][0]['tooltip_function']='0x43eb90';self.bad()
 def test_12_registration_tokens_alone_are_not_proof(self):del self.d['t225_named_trigger_evaluators.json'];self.bad()
 def test_13_claimed_war_boolean_must_match_raw(self):self.d[m.LIVE]['pairs'][0]['named_has_war_with']=False;self.bad()
 def test_14_claimed_byte49_must_match_raw(self):self.d[m.LIVE]['pairs'][0]['war_flag49']=1;self.bad()
 def test_15_country443_maps_to368_not443(self):self.d[m.LIVE]['countries']['368']['tag']=368;self.bad()
 def test_16_claimed_war_pointer_requires_operand(self):self.d[m.LIVE]['pairs'][1]['war_relation']='0x0';self.bad()
 def test_17_generic_handle_namespace_rejected(self):self.d[m.BIND]['same_selected_units'][0]['handle_type']=4713;self.bad()
 def test_18_same_two_controls_not_new_visible_feed(self):
  r=m.replay(self.d);self.assertEqual(r['owner_enemy_subject_ids'],[399,481]);self.assertFalse(r['visible_units_exported']);self.assertNotIn('visible_units',r)
 def test_19_friendly_and_complete_enum_claims_rejected(self):self.d[m.LIVE]['promotion_eligible']=True;self.bad()
 def test_20_split_pdata_requires_closed_remap(self):self.d['t225_tag_remap_closed.json']['functions']['0xc08790']['unresolved_edges']=[{'reason':'open'}];self.bad()
 def test_21_shared_session_guard(self):self.d[m.LIVE]['after']['hour_tick']+=1;self.bad()
 def test_22_shared_code_integrity(self):
  f=self.d['t225_named_trigger_evaluators.json']['functions']['0x3f79e0'];f['raw_hex']='00'+f['raw_hex'][2:];self.bad()
 def test_23_shared_no_live_or_save_backend(self):
  tree=ast.parse((Q/'t225_captured_diplomacy_replay.py').read_text());self.assertEqual([n.name for x in ast.walk(tree) if isinstance(x,(ast.Import,ast.ImportFrom)) for n in x.names],['hashlib','struct'])
 def test_24_shared_no_contract_or_relation_export(self):
  r=m.replay(self.d);self.assertFalse(r['relation_exported']);self.assertFalse(r['complete_input']);self.assertFalse(r['complete_visible_feed'])
