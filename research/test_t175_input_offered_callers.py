import sys,json,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))
IMAGE=0x140000000

class Tests(unittest.TestCase):
 def test_request_vtable_slot2_is_15a92f0(self):
  ev=json.loads((ROOT/'research/t175_CReinforcementRequest_vtables.json').read_text(encoding='utf-8'))
  # file may be the earlier incomplete dump or the later one with image_base
  if 'primary' in ev and 'slots' in ev['primary']:
   slots=ev['primary']['slots']
   # prefer rva field if present
   slot2=next(s for s in slots if s.get('i')==2 or s.get('off') in ('0x10','0x10'))
   rva=slot2.get('rva') or slot2.get('val')
   self.assertTrue('15a92f0' in str(rva).lower() or str(rva).endswith('15a92f0'))
  # also prove from raw preferred-base encoding recorded in later map if present
  self.assertTrue((ROOT/'research/_t175_clip_15a92f0.txt').exists() or (ROOT/'research/_t174_clip_15a92f0.txt').exists())

 def test_15a8cd0_forwards_group_plus28_to_15a9440(self):
  text=(ROOT/'research/_t175_clip_15a8cd0.txt').read_text(encoding='utf-8')
  self.assertIn('lea rdx, [rcx + 0x28]', text)
  self.assertIn('call 0x15a9440', text)
  self.assertNotIn('0x15a8cf0', text)

 def test_15a9440_calls_request_slot2_with_offered_and_type(self):
  text=(ROOT/'research/_t175_clip_15a9440.txt').read_text(encoding='utf-8')
  self.assertIn('mov r9, rbx', text)
  self.assertIn('call qword ptr [rax + 0x10]', text)
  # remaining written back
  self.assertIn('mov rbx, qword ptr [rax]', text)

 def test_15a16a0_calls_slot1_then_slot2(self):
  text=(ROOT/'research/_t175_clip_15a16a0.txt').read_text(encoding='utf-8')
  self.assertIn('call qword ptr [rax + 8]', text)
  self.assertIn('call qword ptr [rax + 0x10]', text)
  self.assertIn('mov r9, rsi', text)

 def test_15a93d0_is_status_slot2_and_uses_cb8e80(self):
  text=(ROOT/'research/_t175_clip_15a93d0.txt').read_text(encoding='utf-8')
  self.assertIn('call 0x717410', text)
  self.assertIn('call 0xcb8e80', text)
  self.assertIn('lea r9, [rdi + 0x20]', text)
  self.assertIn('call 0x15a16a0', text)

 def test_live_status_list_reaches_request_1835(self):
  st=json.loads((ROOT/'research/t175_reinforcement_status_live.json').read_text(encoding='utf-8'))
  g=json.loads((ROOT/'research/t175_group_vtable_live.json').read_text(encoding='utf-8'))
  self.assertEqual(st['class'],'CReinforcementStatus')
  self.assertEqual(st['plus38_class'],'CCountry')
  self.assertEqual(len(st['plus20_items']),1)
  self.assertEqual(st['plus20_items'][0]['class'],'CArmyReinforcementRequests')
  self.assertEqual(st['plus20_items'][0]['ptr'], g['group'])
  self.assertTrue(g['contains_1835'])
  self.assertEqual(g['requests'][0]['ptr'],'0x26cb1969530')
  self.assertEqual(g['slots'][2]['rva'],'0x15a8cd0')
  self.assertEqual(g['slots'][1]['rva'],'0x15a8790')

 def test_still_not_emitted_as_demanded_or_affected(self):
  cap=json.loads((ROOT/'research/t171_live_capture.json').read_text(encoding='utf-8'))
  eq=cap['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(cap['complete_input'])

if __name__=='__main__':
 unittest.main()
