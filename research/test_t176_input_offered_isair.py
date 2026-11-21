import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))

class Tests(unittest.TestCase):
 def test_fe84d0_assert_is_air_and_remaining_formula(self):
  text=(ROOT/'research/_t176_clip_fe84d0.txt').read_text(encoding='utf-8')
  self.assertIn('call 0xcf4e10', text)
  self.assertIn('imul rcx, rax, -0x186a0', text)
  self.assertIn('add rcx, rbx', text)
  self.assertIn('mov qword ptr [r12], rcx', text)
  strs=json.loads((ROOT/'research/_t176_strings_fe84d0.json').read_text(encoding='utf-8'))
  joined=' '.join(s['s'] for s in strs)
  self.assertIn('Expected air equipment.', joined)
  self.assertIn('IsAir()', joined)

 def test_fe86c0_same_remaining_and_is_air_assert(self):
  text=(ROOT/'research/_t176_clip_fe86c0.txt').read_text(encoding='utf-8')
  self.assertIn('imul rcx, rax, -0x186a0', text)
  self.assertIn('add rcx, rbx', text)
  self.assertIn('mov qword ptr [r15], rcx', text)
  strs=json.loads((ROOT/'research/_t176_strings_fe86c0.json').read_text(encoding='utf-8'))
  self.assertTrue(any('Expected air equipment.' in s['s'] for s in strs))

 def test_cf4e10_is_air_bit_test(self):
  text=(ROOT/'research/_t176_clip_cf4e10_full.txt').read_text(encoding='utf-8')
  self.assertIn('mov rax, qword ptr [rbx + 0x5a0]', text)
  self.assertIn('mov rcx, qword ptr [rbx + 0x5a8]', text)
  self.assertIn('call 0x100f620', text)
  self.assertIn('movabs rcx, 0x1f0037fc00', text)
  self.assertIn('setne al', text)

 def test_cb8e80_non_air_passthrough_r9(self):
  text=(ROOT/'research/_t175_clip_cb8e80.txt').read_text(encoding='utf-8')
  self.assertIn('0xcb8f4c  call 0xcf4e10', text)
  self.assertIn('0xcb8f53  je 0xcb9306', text)
  self.assertIn('0xcb9306  mov qword ptr [r13], rbx', text)

 def test_live_infantry_is_not_air_and_status_is_country_f78(self):
  ev=json.loads((ROOT/'research/t176_vtables_and_isair.json').read_text(encoding='utf-8'))
  live=ev['live']
  self.assertFalse(live['is_air_on_type']['is_air'])
  self.assertTrue(live['status_is_f78'])
  self.assertEqual(live['country_plus8'], 44)

 def test_15a93d0_still_only_status_vtable_slot2(self):
  ev=json.loads((ROOT/'research/t176_static_refs.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['caller_counts'].get('15a93d0',0), 0)
  self.assertEqual(ev['caller_funcs'].get('cb8e80'), ['0x15a93d0'])
  self.assertEqual(ev['caller_funcs']['15a16a0'], ['0x15a92c0','0x15a93d0'])
  hits=ev['preferred_base_hits']['15a93d0']
  self.assertEqual(len(hits),1)
  # 0x2a4b878 + 0x10
  self.assertTrue(any(h['rva'] in ('0x2a4b888','0x2a4b888') for h in hits) or hits[0]['rva']=='0x2a4b888')

 def test_717400_callers_are_not_accept(self):
  ev=json.loads((ROOT/'research/t176_717400_callers.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['count'],8)
  self.assertEqual(ev['interesting'],[])
  text=(ROOT/'research/_t176_clip_717400.txt')
  # may be the over-read file; check two-instruction getter from t176 clip start
  raw=(ROOT/'research/_t176_clip_717400.txt').read_text(encoding='utf-8')
  self.assertIn('0x717400  mov rax, qword ptr [rcx + 0xf78]', raw)
  self.assertIn('0x717407  ret', raw)

 def test_15a8f00_is_upgrades_not_reinforcement_driver(self):
  ev=json.loads((ROOT/'research/t176_vtables_and_isair.json').read_text(encoding='utf-8'))
  c=ev['static']['15a8f00_classes'][0]
  self.assertEqual(c['name'],'.?AVCArmyUpgradesStatus@@')
  self.assertEqual(c['slot'],2)

 def test_still_not_emitted_as_demanded_or_affected(self):
  cap=json.loads((ROOT/'research/t171_live_capture.json').read_text(encoding='utf-8'))
  eq=cap['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(cap['complete_input'])

if __name__=='__main__':
 unittest.main()
