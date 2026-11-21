import unittest,json
from pathlib import Path
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from research._t205_flow import walk_flow
P=Path(__file__).resolve().parent
def data(n):return json.loads((P/n).read_text(encoding='utf8'))
class BoundedCFG(unittest.TestCase):
 def f(self,h,start=0x1000,**kw):return walk_flow(Cs(CS_ARCH_X86,CS_MODE_64),bytes.fromhex(h),start,**kw)
 def test_zero_immediate_loop(self):
  d=self.f('ebfe',0);self.assertEqual(d['reachable_instruction_count'],1);self.assertEqual(d['unresolved_edges'],[])
 def test_cold_branch_survives_truncation(self):
  d=self.f('85c07402c390b801000000c3');self.assertEqual(d['reachable_instruction_count'],5);self.assertTrue(any(s.startswith('1006 mov')for s in d['asm']))
 def test_indirect_not_fallthrough(self):
  d=self.f('ff2090c3');self.assertEqual(d['reachable_instruction_count'],1);self.assertEqual(d['unresolved_edges'][0]['reason'],'indirect jump')
 def test_calls_opaque(self):
  d=self.f('e801000000c3cc');self.assertEqual(d['reachable_instruction_count'],2);self.assertEqual(len(d['calls']),1);self.assertFalse(any(s.startswith('1006 ')for s in d['asm']))
 def test_outside_conditional_recorded(self):
  d=self.f('7407c3');self.assertEqual(d['reachable_instruction_count'],2);self.assertEqual(d['unresolved_edges'][0]['reason'],'conditional target outside window')
 def test_external_tail_recorded(self):
  d=self.f('e900100000');self.assertEqual(d['external_tails'][0]['target'],'0x2005');self.assertEqual(d['unresolved_edges'],[])
 def test_step_bound_fails_closed(self):
  with self.assertRaises(ValueError):self.f('9090c3',max_steps=2)
 def test_bad_decode_not_silent(self):self.assertEqual(self.f('0f')['unresolved_edges'][0]['reason'],'decode/end failure')
 def test_trap_stops(self):self.assertEqual(self.f('0f0b90c3')['reachable_instruction_count'],1)
 def test_outside_entry_reported(self):self.assertEqual(self.f('c3',entry=0x2000)['unresolved_edges'][0]['reason'],'outside window')
class NativeEvidence(unittest.TestCase):
 def names(self):return{x['token']:x['name']for x in data('t205_supply_native_keyword_names_v5.json')['matched']}
 def test_known_positive_and_identity_wrapper(self):
  d=data('t205_supply_native_keyword_names_v5.json');self.assertEqual(self.names()['0x3750'],'manpower_lost');self.assertEqual(d['verified_identity_ctor']['asm'],['153750 mov dword ptr [rcx], edx','153752 mov rax, rcx','153755 ret '])
 def test_complete_direct_windows_not_global_claim(self):
  d=data('t205_lifecycle_initial_flows.json')['flows']
  for a,n in(('0x1349260',345),('0xd3f020',295),('0xd3f4d0',42)):self.assertEqual(d[a]['reachable_instruction_count'],n);self.assertEqual(d[a]['unresolved_edges'],[])
 def test_leader_selection_not_people_reset(self):
  d=data('t205_lifecycle_initial_flows.json')['flows']['0xd3f4d0'];s='\n'.join(d['asm']);self.assertEqual(d['calls'],[]);self.assertIn('mov qword ptr [rdi + 0x260], rcx',s);self.assertNotIn(' + 0x60]',s);self.assertEqual(self.names()['0x3755'],'leader_hours');self.assertEqual(self.names()['0x28b7'],'leader')
 def test_modifier_hours_not_duration(self):
  self.assertEqual(self.names()['0x375c'],'modifier_hours');s=(P/'_t204_clip_d40ba0.txt').read_text(encoding='utf8');self.assertIn('d40c8b mov rbx, qword ptr [r14 + 0x1d8]',s);self.assertIn('d40c96 mov edx, 0x375c',s);self.assertEqual(0x230-0x58,0x1d8)
 def test_air_factor_not_equipment_or_people(self):self.assertEqual(self.names()['0x3751'],'manpower_lost_air_factor');self.assertEqual(self.names()['0x3753'],'equipment_lost')
 def test_capture_recovery_distinct(self):self.assertEqual(self.names()['0x3850'],'equipment_captured_by_enemy');self.assertEqual(self.names()['0x4cb2'],'equipment_recovered')
 def test_motorization_byte_not_bool(self):
  self.assertEqual(self.names()['0x4de7'],'motorization_level');s='\n'.join(data('t205_supply_base_and_combat_dispatch.json')['supply_base_parser']['asm']);self.assertIn('mov byte ptr [rbx + 0x1d], al',s);self.assertNotIn(' + 0x1e]',s)
 def test_disrupted_supply_not_total_gap(self):self.assertEqual(self.names()['0x4cf2'],'disrupted_supply')
 def test_progress_damage_weather_win_not_time_orientation(self):
  n=self.names();self.assertEqual([n[x]for x in('0x2b05','0x376b','0x2f04','0xe3')],['progress','total_damage','snow','win'])
 def test_checksum_native_constants_and_return_usage(self):
  d=data('t205_lifecycle_initial_flows.json');s='\n'.join(d['functions']['0x2573160']['asm']);self.assertIn('0xcc9e2d51',s);self.assertIn('0x1b873593',s);e=[x for x in data('t205_close_checksum_dispatch.json')['edges']if x['target']=='0xf42ad0'];self.assertEqual(len(e),2);self.assertTrue(any('call 0x2573160'in s for x in e for s in x['context']))
 def test_ordinary_close_precedes_detach_erase_delete(self):
  d=data('t205_v70_global_dispatch_candidates.json');a=next(x['context']for x in d['candidates']if x['site']=='0xc0df51');s='\n'.join(a);self.assertLess(s.index('c0df51 call'),s.index('c0df5b call'));self.assertLess(s.index('c0df5b call'),s.index('c0df66 call'));self.assertLess(s.index('c0df66 call'),s.index('c0df7c call'))
 def test_side_callback_not_combat_or_army_same_slot(self):
  d=data('t205_side_callback_and_timer_dispatch.json');self.assertEqual(d['class'],'.?AVCLandCombatant@@');self.assertEqual(d['methods']['0x108'],'0x133e700');d=data('t205_close_checksum_dispatch.json')['virtual_bindings'];self.assertEqual(d[0]['methods']['0x70'],'0x1349260')
 def test_timer_writes_are_increments_not_timestamps(self):
  d=data('t205_side_callback_and_timer_dispatch.json')['flows'];self.assertIn('1348025 inc dword ptr [rbx + 0x44]',d['0x1347fd0']['asm']);self.assertIn('1348da5 inc dword ptr [rbx + 0x40]',d['0x1348d30']['asm'])
 def test_global_writer_controls_and_nonexhaustive_scope(self):
  d=data('t205_global_flag_write_candidates.json');self.assertEqual(d['raw_hits'],437);self.assertEqual(len(d['write_sites']),346);self.assertEqual(len(d['unbound_hits']),4);self.assertTrue(any(x['site']=='0xc4e1b9'for x in d['write_sites']));self.assertTrue(any(x['site']=='0xca4abd'for x in d['write_sites']));self.assertIn('Not exhaustive',d['scope'])
class ContractAcceptance(unittest.TestCase):
 def test_pending_only_existing_two_rows(self):
  d=data('t205_promotions_pending_inventory.json');self.assertFalse(d['applied']);self.assertEqual(d['t205_new_promotions'],[]);self.assertEqual(len(d['proof_accepted_pending_sync']),2);self.assertEqual(d['projected_inventory_after_sync'],{'verified':74,'unverified':42});self.assertEqual([d['last_confirmed_inventory'][k]for k in('tables','fields','columns')],[14,116,3]);self.assertIsNone(d['current_D_readback_sha256'])
 def test_existing_full_exports_remain_incomplete(self):
  from jsonschema import Draft202012Validator
  s=json.loads((P.parent/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf8'))
  for z in('a','b'):
   d=data(f't201_full_capture_recursive_{z}.json');e=list(Draft202012Validator(s).iter_errors(d['observation']));self.assertFalse(d['complete_input']);self.assertEqual(len(e),52);self.assertTrue(all(x.validator=='required'for x in e))
