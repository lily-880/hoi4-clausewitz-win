import unittest,json,struct,ast,hashlib
from pathlib import Path
import t227_qualified_crisis_replay as m
Q=Path(__file__).parent
class CrisisWitnessTests(unittest.TestCase):
 def setUp(self):
  self.d={p.name:json.loads(p.read_text()) for p in Q.glob('t227_*.json') if p.name!='t227_native_code_pins.json'}
 def bad(self):
  with self.assertRaises(m.Unproved):m.replay(self.d)
 def test_01_original_domain_is_taskforce_airbase(self):
  r=m.replay(self.d);self.assertEqual(r['qualified_evidence'][0]['unit_ids'],[479]);self.assertEqual(self.d['t227_live_registry_type_bindings.json']['rows'][1]['first_class'],'.?AVCTaskForce@@')
 def test_02_base5_6_not_land3_4(self):
  d=self.d['t227_supply_alert_mapping_consumers.json']['functions']['0xb867b0'];d['asm'][d['asm'].index('b86cac add edx, 5')]='b86cac add edx, 3';self.bad()
 def test_03_actual_cached_alert4_group(self):self.assertEqual(m.replay(self.d)['native_group_alert_id'],4)
 def test_04_theatergroup_not_theatre_plus48(self):self.d[m.LIVE]['membership'][0]['theatre']=self.d[m.LIVE]['membership'][0]['theater_group'];self.bad()
 def test_05_actual479_dual_semantic_witness(self):self.assertEqual(m.replay(self.d)['qualified_evidence'],[{'kind':'out_of_supply','unit_ids':[479],'province_ids':[1780]}])
 def test_06_genuine374_negative_excluded(self):
  r=m.replay(self.d);n=next(x for x in r['control_audit'] if x['unit_id']==374);self.assertEqual((n['native_bucket'],n['out_of_supply']),(2,False));self.assertNotIn(374,r['qualified_evidence'][0]['unit_ids'])
 def test_07_intermediate500_not_whole_group_export(self):
  r=m.replay(self.d);a=next(x for x in r['control_audit'] if x['unit_id']==500);self.assertEqual((a['native_bucket'],a['source'],a['effective'],a['out_of_supply']),(1,38271,38451,True));self.assertNotIn(500,r['qualified_evidence'][0]['unit_ids'])
 def test_08_zero_minimum_dominates_unread_members(self):
  r=m.replay(self.d);self.assertEqual(r['native_group_minimum'],0);self.assertEqual(self.d[m.LIVE]['inspected'],3);self.assertEqual(self.d[m.LIVE]['membership'][0]['member_count'],25)
 def test_09_synthetic_grace_alert_not_outof_supply(self):
  effective,out,b=m.supply(1000,1,7200000,72,99000,False);self.assertEqual((effective,out,b),(100000,False,0));self.assertFalse(m.qualifies(b,out,False))
 def test_10_cached_group_key_must_match(self):self.d[m.ACTIVE]['active']['4']['rows'][0]['key_group']='0x0';self.bad()
 def test_11_named_active_alert_mandatory(self):self.d[m.ACTIVE]['active']['4']['rows'][0]['name']='alert_base_very_low_supply';self.bad()
 def test_12_absent_actual_alert4_rejected(self):self.d[m.ACTIVE]['active']['4']['count']=0;self.bad()
 def test_13_out_predicate_threshold_raw_not_name(self):self.d[m.LIVE]['rows'][2]['supply_evidence']['threshold_raw']=20000;self.bad()
 def test_14_actual_positive_required(self):self.d[m.LIVE]['positive']['unit_id']=374;self.bad()
 def test_15_sample_roles_cannot_be_swapped(self):self.d[m.LIVE]['negative']['unit_id']=479;self.bad()
 def test_16_actual_membership_backlink_mandatory(self):self.d[m.LIVE]['rows'][2]['orders_group']='0x0';self.bad()
 def test_17_member_adjustment_static_proof_required(self):
  f=self.d['t227_land_member_virtual_adjustments.json']['functions']['0xc4f050'];f['asm'][0]='c4f050 lea rax, [rcx - 0x10]';self.bad()
 def test_18_primary_identity_static_proof_required(self):
  f=self.d['t227_land_member_virtual_adjustments.json']['functions']['0x20f350'];f['asm'][0]='20f350 xor eax, eax';self.bad()
 def test_19_synthetic_special_exemption(self):
  eff,out,b=m.supply(0,1,0,72,99000,True);self.assertEqual((out,b),(False,2));self.assertFalse(m.qualifies(b,out,True))
 def test_20_no_severity_from_threshold_or_alert_id(self):
  r=m.replay(self.d);self.assertFalse(r['severity_exported']);self.assertNotIn('severity',r['qualified_evidence'][0])
 def test_21_not_complete_crisis_or_Input(self):
  r=m.replay(self.d);self.assertFalse(r['complete_crisis_record']);self.assertFalse(r['complete_input']);self.assertFalse(r['notes_exported']);self.assertNotIn('notes',r['qualified_evidence'][0])
 def test_22_current_province_join_required(self):self.d[m.LIVE]['rows'][2]['province_id']=1790;self.bad()
 def test_23_source_effective_independent_raw_replay(self):self.d[m.LIVE]['rows'][2]['effective_raw']=100000;self.bad()
 def test_24_schema_kind_is_composed_not_raw_enum(self):self.assertTrue(m.replay(self.d)['kind_is_composed_schema_annotation_not_raw_Crisis_enum'])
 def test_25_dispatcher_not_claimed_globally_closed(self):self.d['t227_alert_manager_update_root.json']['functions']['0xb6b9e0']['unresolved_edges']=[];self.bad()
 def test_26_witness_only_not_complete_crisis_feed(self):
  r=m.replay(self.d);self.assertFalse(r['complete_crisis_feed']);self.assertEqual(len(r['qualified_evidence'][0]['unit_ids']),1)
 def test_27_native_land_alert4_mapping_not_reversed(self):
  f=self.d['t227_supply_alert_mapping_consumers.json']['functions']['0xb79d00'];j=f['asm'].index('b79e17 mov edx, 4');f['asm'][j]='b79e17 mov edx, 3';self.bad()
 def test_28_shared_inventory_shape_exact_three_rows(self):
  a=(Q/'t227_inventory_before.md').read_bytes();b=(Q/'t227_inventory_proposed.md').read_bytes();self.assertEqual(hashlib.sha256(a).hexdigest(),'ebd57b52a517d88e51e39b10f3c3b529e2ce2b542e9fde5ebd9f9d2cb1871ae5');self.assertEqual(hashlib.sha256(b).hexdigest(),'8c51a0318d5d72dc3b0d2a67325462c16c42629abffddb1438f18b774e636740');la=a.decode().splitlines();lb=b.decode().splitlines();self.assertEqual(len(la),len(lb));diff=[(x,y) for x,y in zip(la,lb) if x!=y];self.assertEqual(len(diff),3);rows=[x for x in lb if x.startswith('|') and not x.startswith(('| 字段名','| ---'))];self.assertEqual((sum(x.startswith('| 字段名') for x in lb),len(rows),sum('| 已验证 |' in x for x in rows),sum('| 未验证 |' in x for x in rows)),(14,116,86,30));self.assertTrue(all(len(x.split('|'))==5 for x in rows));self.assertEqual(a.count(b'\r\r\n'),b.count(b'\r\r\n'))
 def test_29_shared_native_code_hash(self):
  f=self.d['t227_supply_alert_mapping_consumers.json']['functions']['0xb79d00'];f['raw_hex']='00'+f['raw_hex'][2:];self.bad()
 def test_30_shared_session_guard(self):self.d[m.LIVE]['after']['hour_tick']+=1;self.bad()
 def test_31_shared_no_game_backend(self):
  t=ast.parse((Q/'t227_qualified_crisis_replay.py').read_text());self.assertEqual([n.name for x in ast.walk(t) if isinstance(x,(ast.Import,ast.ImportFrom)) for n in x.names],['hashlib','struct'])
 def test_32_shared_type51_gate(self):self.d[m.LIVE]['rows'][2]['handle_type']=4713;self.bad()
