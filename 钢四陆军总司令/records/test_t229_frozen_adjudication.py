import unittest,json,copy,struct,hashlib,ast
from pathlib import Path
import t229_frozen_adjudication as m
Q=Path(__file__).resolve().parent
BASE=tuple(json.loads((Q/n).read_text()) for n in ('t229_history_winner_probe.json','t229_winner_semantics_and_ally_pivot.json','t229_named_pivot_closure.json'))
def patch(d,a,b):
 seen=set()
 for row in d['raw_dependencies']:
  lo=int(row['address'],16);raw=bytearray.fromhex(row['hex'])
  for i,v in enumerate(b):
   if lo<=a+i<lo+len(raw):raw[a+i-lo]=v;seen.add(i)
  row['hex']=raw.hex()
 assert len(seen)==len(b)
class HistoryBridgeTests(unittest.TestCase):
 def setUp(self):self.a,self.b,self.c=copy.deepcopy(BASE)
 def result(self):return m.replay(self.a,self.b,self.c)
 def bad(self,msg):
  with self.assertRaisesRegex(m.Unproved,msg):self.result()
 def test_01_genuine_record212_group_win(self):
  r={x['history_pool_index']:x for x in self.result()['retained_research_results']};self.assertTrue(r[212]['group_won']);self.assertEqual(r[212]['side_selector'],0)
 def test_02_genuine_record5_group_loss(self):
  r={x['history_pool_index']:x for x in self.result()['retained_research_results']};self.assertFalse(r[5]['group_won']);self.assertEqual(r[5]['side_selector'],1)
 def test_03_same_selector_different_outcomes(self):
  r={x['history_pool_index']:x for x in self.result()['retained_research_results']};self.assertEqual(r[214]['side_selector'],r[5]['side_selector']);self.assertNotEqual(r[214]['group_won'],r[5]['group_won'])
 def test_04_different_sides_both_initial_rows_win(self):
  r={x['history_pool_index']:x for x in self.result()['retained_research_results']};self.assertNotEqual(r[212]['side_selector'],r[214]['side_selector']);self.assertTrue(r[212]['group_won'] and r[214]['group_won'])
 def test_05_explicit_win_keyword_not_attacker(self):
  next(x for x in self.b['tokens'] if x['token']==0xe3)['actual_name']='attacker';self.bad('native keyword name')
 def test_06_defensive_victory_has_own_named_field(self):
  t={x['token']:x['actual_name'] for x in self.b['tokens']};self.assertEqual(t[0x3756],'defensive_victory');self.result()
 def test_07_player_attacker_not_win_keyword(self):
  t={x['token']:x['actual_name'] for x in self.b['tokens']};self.assertEqual(t[0x4dbc],'player_is_attacker');self.assertNotEqual(t[0x4dbc],t[0xe3]);self.result()
 def test_08_actual_active_ids_outside247_pool(self):
  r=self.result();self.assertEqual(r['active_id_controls'],[3072,3096,3097]);self.assertEqual(r['pool_count'],247);self.assertFalse(r['native_active_history_id_bridge'])
 def test_09_boolean_claim_not_bridge_certificate(self):
  self.b['history_active_bridge_proved']=True;self.bad('no independent bridge certificate')
 def test_10_cannot_rename_poolindex_as_live_combat_id(self):
  self.a['active_controls'][0]['combat_id']=212;self.bad('native active handle')
 def test_11_retained_reference_bounds_fail_closed(self):
  row=self.b['references'][0];patch(self.b,int(row['reference_address'],16),struct.pack('<I',247));self.bad('pool index bound')
 def test_12_wrong_group_rejected_before_deref(self):
  self.b['references'][0]['group']='0x10000000';self.bad('group membership')
 def test_13_nonboolean_selector_rejected(self):
  row=self.b['references'][0];patch(self.b,int(row['reference_address'],16)+4,b'\x02');self.bad('native boolean inputs')
 def test_14_nonboolean_defensive_flag_rejected(self):
  row=self.b['references'][0];patch(self.b,int(row['record'],16)+0x444,b'\x02');self.bad('native boolean inputs')
 def test_15_declared_winner_without_raw_support_rejected(self):
  self.b['references'][0]['native_group_won_reconstructed']=False;self.bad('raw win reconstruction')
 def test_16_missing_flag_dependency_rejected(self):
  a=int(self.b['references'][0]['record'],16)+0x444;self.b['raw_dependencies']=[x for x in self.b['raw_dependencies'] if not int(x['address'],16)<=a<int(x['address'],16)+x['size']];self.bad('missing raw dependency')
 def test_17_ui_switches_not_falsely_closed(self):
  self.a['ui_function']['unresolved_edges']=[];self.bad('UI remains partial')
 def test_18_no_schema_result_or_dates_from_correlation(self):
  r=self.result();self.assertFalse(r['result_exported']);self.assertEqual(r['schema_combats'],[]);self.assertNotIn('started_at',r);self.assertNotIn('ended_at',r);self.assertEqual(r['new_promotions'],0)
 def test_19_named_common_war_consumer_not_classname_only(self):
  self.c['named_literals']=[x for x in self.c['named_literals'] if x['text']!='TRIGGER_HAS_WAR_TOGETHER_WITH'];self.bad('independent named common-war consumer')
 def test_20_neighbor_losing_side_assertion_not_leaf_semantics(self):
  r=self.result();self.assertEqual(r['common_war_flag_offset'],'0x310');self.assertIn('Checking IsOnLosingSide on country that is not in war relation',r['ignored_unreachable_neighbor_literals'])
 def test_21_allied_scope_faction_precondition_not_new_friend(self):
  r=self.result();self.assertTrue(r['allied_scope_uses_faction_roster']);self.assertEqual(r['new_foreign_friendly_positives'],0);self.assertFalse(r['relation_exported'])
 def test_22_short_factory_not_full_trigger_interface(self):
  self.c['full_trigger_bindings'].append({'class_name':'.?AV?$CTriggerEntry@VCHasWarTogetherTrigger@@@@','slots':{}});self.bad('reject short factory interfaces')
 def test_23_ordinary_trigger_has_no_proved_C0_slot(self):
  row=next(x for x in self.c['full_trigger_bindings'] if 'HasWarTogether' in x['class_name']);row['slots']['0xc0']='0x4517e0';self.bad('virtual slot bound')
 def test_24_common_war_not_friendly_enum_or_nonwar_inference(self):
  self.c['new_friendly_samples']=1;self.bad('no faction loop or invented friend positive')
 def test_25_existing_crisis_scope_preserved_no_new_feed(self):
  r=self.result();self.assertIn('3/25',r['notes_scope_preserved']);self.assertIn('kind composed',r['notes_scope_preserved']);self.assertFalse(r['complete_crisis_feed']);self.assertFalse(r['complete_input'])
 def test_26_shared_inventory_byte_identical87_29(self):
  a=(Q/'t229_inventory_before.md').read_bytes();self.assertEqual(hashlib.sha256(a).hexdigest(),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3');s=a.decode();self.assertEqual(s.count('| 字段名 | 已验证/未验证 | 说明 |'),14);self.assertEqual(s.count('| 已验证 |'),87);self.assertEqual(s.count('| 未验证 |'),29);self.assertEqual(sum('| 已验证 |' in x or '| 未验证 |' in x for x in s.splitlines()),116)
 def test_27_shared_native_integrity(self):
  self.c['functions']['0xd86fe0']['raw_hex']='00';self.bad('native integrity')
 def test_28_shared_session_drift_rejected(self):
  self.b['after']['hour_tick']+=1;self.bad('unstable guard')
 def test_29_shared_production51_four_hash_baseline(self):
  d=json.loads((Q/'t228_final_seal.json').read_text());self.assertEqual(d['production_baseline_fields'],51);self.assertEqual(len(d['production_hashes']),4);self.assertTrue(d['fingerprint_gates_unchanged'])
 def test_30_shared_adjudicator_has_no_IO_or_game_backend(self):
  a=ast.parse((Q/'t229_frozen_adjudication.py').read_text());ii={n.module for n in ast.walk(a) if isinstance(n,ast.ImportFrom)}|{x.name for n in ast.walk(a) if isinstance(n,ast.Import) for x in n.names};self.assertLessEqual(ii,{'hashlib','struct','t227_qualified_crisis_replay'});self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in {'open','Runtime','Proc','exec','eval'} for n in ast.walk(a)))
