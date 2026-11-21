import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))

class Tests(unittest.TestCase):
 def test_d71b60_only_two_e8_callers(self):
  ev=json.loads((ROOT/'research/t178_e8_and_strings.json').read_text(encoding='utf-8'))
  self.assertCountEqual(ev['e8']['d71b60']['funcs'],['0xd71810','0xd724e0'])
  self.assertEqual(ev['e8']['d71810']['funcs'],['0x72f220'])
  self.assertEqual(ev['e8']['72f220']['funcs'],['0x1eae60'])
  self.assertEqual(ev['e8']['d6f140']['funcs'],['0xd71b60'])
  self.assertEqual(ev['e8']['15a93d0']['count'],0)
  self.assertEqual(ev['e8']['cb8e80']['funcs'],['0x15a93d0'])

 def test_d724e0_callers_zero_status_args(self):
  for name in ('_t178_clip_d47380.txt','_t178_clip_d4b860.txt'):
    text=(ROOT/'research'/name).read_text(encoding='utf-8')
    self.assertIn('xor r9d, r9d', text)
    self.assertIn('xor r8d, r8d', text)
    self.assertIn('xor edx, edx', text)
    self.assertIn('mov rcx, qword ptr [rax + 0xf70]', text)
    self.assertIn('call 0xd724e0', text)

 def test_gamestate_hourly_does_not_call_accept(self):
  leas=json.loads((ROOT/'research/t178_hourly_profile_leas.json').read_text(encoding='utf-8'))
  self.assertTrue(any(x['dest']=='0x27a0810' and x['func']=='0x1f5230' and x['s']=='gamestate.hourly' for x in leas))
  text=(ROOT/'research/_t178_clip_1f5230.txt').read_text(encoding='utf-8')
  for forbidden in ('0xd71b60','0xd71810','0xd724e0','0x72f220','0x15a93d0','0x15aa9c0','0x140b9c0','0xce4fc0','0x717400','0xd6f140'):
    self.assertNotIn('call '+forbidden, text)
  ev=json.loads((ROOT/'research/t178_hourly_funcs.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['1e5660']['e8_funcs'],['0x1f5230'])
  self.assertEqual(ev['202f30']['e8_funcs'],['0x1f5230'])
  self.assertEqual(ev['1e5660']['hits'],['0x1e5660  mov rax, rsp'])  # false-positive start, no real key
  # ensure no interesting callees
  for name in ('1e5660','202f30'):
    calls=ev[name]['direct_calls']
    for c in calls:
      self.assertFalse(any(c.startswith(p) for p in ('0xd71','0xd72','0xd718','0x72f2','0x15a9','0x15aa','0x140b','0xce4f','0x7174','0xd6f1')), c)

 def test_15aa9c0_is_request_and_logistics_not_accept(self):
  ev=json.loads((ROOT/'research/t178_hourly_funcs.json').read_text(encoding='utf-8'))
  text=(ROOT/'research/_t178_clip_15aa9c0.txt').read_text(encoding='utf-8')
  self.assertIn('call 0x15a26f0', text)
  self.assertIn('call 0x140b9c0', text)
  self.assertNotIn('call 0x15a93d0', text)
  self.assertNotIn('call 0xd71b60', text)
  self.assertIn('0x15aaef8  call qword ptr [rax + 0x10]', text)
  # allocator free pattern: no r8/r9 setup immediately before
  win='\n'.join(l for l in text.splitlines() if 0x15aaede<=int(l.split()[0],16)<=0x15aaef8)
  self.assertIn('test rdx, rdx', win)
  self.assertNotIn('mov r9', win)
  self.assertNotIn('mov r8', win)
  self.assertEqual(ev['15ab390']['e8_funcs'],['0xce4fc0'])

 def test_ce4fc0_is_carmy_slot18(self):
  ev=json.loads((ROOT/'research/t178_e8_and_strings.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['e8']['ce4fc0']['count'],0)
  # vtable proof lives in the live/static dump written this batch
  meta=json.loads((ROOT/'research/t178_hourly_vs_daily_accept.json').read_text(encoding='utf-8'))
  self.assertIn('0x29d6d98 slot 18', meta['hourly_request_not_accept']['ce4fc0'])

 def test_still_not_emitted_as_demanded_or_affected(self):
  cap=json.loads((ROOT/'research/t171_live_capture.json').read_text(encoding='utf-8'))
  eq=cap['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(cap['complete_input'])

if __name__=='__main__':
 unittest.main()
