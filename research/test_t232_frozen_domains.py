import unittest,json,copy,inspect,ast
from pathlib import Path
import t232_frozen_domains as m
Q=Path(__file__).resolve().parent
FILES={'session':'t232_initial_session_rebind.json','domain':'t232_correct_priority_domain.json','level':'t232_alert_level_domain.json','tokens':'t232_live_token_names.json','pivot':'t232_front_invalidation_pivot.json','pins':'t232_accepted_native_pins.json'}
def payload():
 p={k:json.loads((Q/n).read_text()) for k,n in FILES.items()};p['inventory']=(Q/'t232_inventory_before.md').read_bytes();return p
def overwrite(d,addr,raw):
 for row in d['raw_dependencies']:
  a=int(row['address'],16);b=bytearray.fromhex(row['hex'])
  for i,v in enumerate(raw):
   if a<=addr+i<a+len(b):b[addr+i-a]=v
  row['hex']=b.hex()
class DomainTests(unittest.TestCase):
 def test_01_new_session_actual_positive_witness_and_healthy_negative(self):
  r=m.replay(**payload());self.assertEqual(r['qualified_witness_unit_ids'],[479]);self.assertEqual(r['healthy_control_unit_ids'],[374])
 def test_02_corrected_second_pointer_not_mistranscribed_RVA(self):
  p=payload();p['domain']['method1_rva']='0x1eafb08'
  with self.assertRaisesRegex(m.Unproved,'corrected pointer arithmetic'):m.replay(**p)
 def test_03_secondary_interface_adjustor_not_full_object(self):
  p=payload();p['domain']['current_col_hex']='0100000000000000'+p['domain']['current_col_hex'][16:]
  with self.assertRaisesRegex(m.Unproved,'navy secondary identity'):m.replay(**p)
 def test_04_priority_high_normal_names_independent_but_wrong_domain(self):
  r=m.replay(**payload());self.assertEqual(r['priority_domain'],'navy UI secondary interface');self.assertEqual(r['schema_severity_samples'],0)
 def test_05_missing_priority_literal_rejected(self):
  p=payload();p['domain']['functions']['0x1eeff60']['reachable_literals']=[]
  with self.assertRaisesRegex(m.Unproved,'named priority consumer'):m.replay(**p)
 def test_06_navy_priority_not_schema_severity(self):
  p=payload();p['claims']={'severity_from_priority':True}
  with self.assertRaisesRegex(m.Unproved,'no schema severity mapping'):m.replay(**p)
 def test_07_occupation_native_enum_is_low0_medium1_high2(self):
  self.assertEqual(m.replay(**payload())['native_occupation_enum'],{'low':0,'medium':1,'high':2})
 def test_08_live_token_string_not_cached_map_only(self):
  p=payload();f=m.Frozen(p['tokens']);tp=f.q(m.BASE+0x368f5a0);overwrite(p['tokens'],tp+19364*32,b'X')
  with self.assertRaisesRegex(m.Unproved,'live token strings'):m.replay(**p)
 def test_09_token_table_must_be_initialized(self):
  p=payload();overwrite(p['tokens'],m.BASE+0x368f570,b'\x00')
  with self.assertRaisesRegex(m.Unproved,'initialized token bound'):m.replay(**p)
 def test_10_occupation_parser_not_land_alert_definition(self):
  p=payload();p['level']['parser_slot_identities'][0]['class']='.?AVCAlert@@'
  with self.assertRaisesRegex(m.Unproved,'occupation parser identity'):m.replay(**p)
 def test_11_occupation_enum_not_generic_watch_high_critical(self):
  p=payload();p['claims']={'severity_from_occupation_enum':True}
  with self.assertRaisesRegex(m.Unproved,'no schema severity mapping'):m.replay(**p)
 def test_12_parser_remains_partial_outside_selected_path(self):
  p=payload();p['domain']['candidate_functions']['0x145e1c0']['unresolved_edges']=[]
  with self.assertRaisesRegex(m.Unproved,'parser partial retained'):m.replay(**p)
 def test_13_exact_parser_enum_store_atoms_required(self):
  p=payload();p['domain']['candidate_functions']['0x145e1c0']['asm'].remove('145e4b4 mov dword ptr [rcx + 0xc8], 2')
  with self.assertRaisesRegex(m.Unproved,'semantic atoms'):m.replay(**p)
 def test_14_registered448_five_is_not_schema_severity(self):
  p=payload();p['claims']={'severity_from448':True}
  with self.assertRaisesRegex(m.Unproved,'no schema severity mapping'):m.replay(**p)
 def test_15_no_scope_expansion_from3_to25(self):
  p=payload();p['level']['sampled_members']=25
  with self.assertRaisesRegex(m.Unproved,'three member scope'):m.replay(**p)
 def test_16_missing_raw_witness_dependency_rejected(self):
  p=payload();p['level']['raw_dependencies']=[]
  with self.assertRaisesRegex(m.Unproved,'missing dependency'):m.replay(**p)
 def test_17_no_notes_payload_reread_or_full_feed(self):
  p=payload();p['claims']={'notes_read':True}
  with self.assertRaisesRegex(m.Unproved,'no scope expansion'):m.replay(**p)
 def test_18_rebuildfronts_command_name_not_invalidation_state(self):
  p=payload();self.assertTrue(any(x['text']=='rebuildfronts' for x in p['pivot']['named_strings']));p['claims']={'front_invalidated_from_log':True}
  with self.assertRaisesRegex(m.Unproved,'no invalidation from log'):m.replay(**p)
 def test_19_loader_error_does_not_prove_war_change_invalidated(self):
  p=payload();self.assertTrue(any('Front refers to invalid country tag' in x['text'] for x in p['pivot']['named_strings']));self.assertEqual(m.replay(**p)['front_invalidated_samples'],0)
 def test_20_actual_active4_subject_not_old_heap_pointer(self):
  p=payload();lm=m.Frozen(p['level']);manager=lm.q(int(p['session']['before']['idler'],16)+0x7a8);head=manager+(4+0xf0e)*24;ptr=lm.q(head);overwrite(p['level'],ptr+0x440,(0).to_bytes(8,'little'))
  with self.assertRaisesRegex(m.Unproved,'qualified cached witness'):m.replay(**p)
 def test_21_shared_inventory_exact_bytes_no_promotion(self):
  p=payload();self.assertEqual(m.replay(**p)['promotions'],[]);p['inventory']+=b'X'
  with self.assertRaisesRegex(m.Unproved,'inventory'):m.replay(**p)
 def test_22_shared_raw_native_integrity(self):
  p=payload();f=p['domain']['functions']['0x1eeff60'];f['raw_hex']='00'+f['raw_hex'][2:]
  with self.assertRaisesRegex(m.Unproved,'native integrity'):m.replay(**p)
 def test_23_shared_restart_stale_snapshot_and_open_gate_rejection(self):
  p=payload();p['session']['before']['pid']=10288
  with self.assertRaisesRegex(m.Unproved,'restarted identity'):m.replay(**p)
  p=payload();p['session']['before']['markers']['safe_land_tool_gate.OPEN']=True
  with self.assertRaisesRegex(m.Unproved,'session safety'):m.replay(**p)
 def test_24_shared_checker_no_process_game_or_IO_backend(self):
  s=inspect.getsource(m);tree=ast.parse(s);names={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
  self.assertTrue({'open','Runtime','Proc','exec','eval'}.isdisjoint(names));self.assertNotIn('subprocess',s)
