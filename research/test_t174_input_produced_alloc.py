import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))

HI=0x53e2d620fb40
LO=0xffffac1d29df04c0  # signed negative cap, same as 1409810

def give(need, produced, offered):
    deficit=need-produced
    if deficit<0: deficit=0
    return offered if offered<deficit else deficit

class Tests(unittest.TestCase):
 def test_15b1da0_uses_same_caps_as_1409810(self):
  text=(ROOT/'research/_t174_clip_15b1da0.txt').read_text(encoding='utf-8')
  self.assertIn('0x53e2d620fb40', text)
  self.assertIn('0xffffac1d29df04c0', text)
  self.assertIn('add rcx, rdx', text)
  # not a return-of-allocated-amount function: it stores into [r9]
  self.assertIn('mov qword ptr [r9], rcx', text)

 def test_140b9c0_and_140b810_mode_sets(self):
  a=(ROOT/'research/_t173_func_140b9c0.txt').read_text(encoding='utf-8')
  # modes 1, 0, then tail jmp 14075c0 with edx=6
  self.assertIn('mov edx, 1', a)
  self.assertIn('xor edx, edx', a)
  self.assertIn('mov edx, 6', a)
  self.assertIn('jmp 0x14075c0', a)
  b=(ROOT/'research/_t174_clip_140b810.txt').read_text(encoding='utf-8')
  self.assertIn('mov edx, 4', b)
  self.assertIn('xor edx, edx', b)
  self.assertIn('mov edx, 6', b)
  self.assertIn('jmp 0x14075c0', b.split('int3')[0])

 def test_15a92f0_give_is_min_deficit_and_offered(self):
  # 15a92f0: deficit=max(0, need-produced); give=min(deficit, offered)
  self.assertEqual(give(80,0,3),3)
  self.assertEqual(give(80,0,80),80)
  self.assertEqual(give(80,3,10),10)
  self.assertEqual(give(80,3,100),77)
  self.assertEqual(give(80,80,3),0)
  text=(ROOT/'research/_t174_clip_15a92f0.txt').read_text(encoding='utf-8')
  self.assertIn('lea rcx, [rbp + 0x38]', text)
  self.assertIn('call 0x1092b70', text)
  self.assertIn('lea rcx, [rbp + 0x78]', text)
  self.assertIn('call 0x10948a0', text)

 def test_15a26f0_inits_produced_empty_and_writes_need(self):
  text=(ROOT/'research/_t171_func_0x15a26f0.txt').read_text(encoding='utf-8')
  self.assertIn('lea rcx, [rsi + 0x38]', text)
  self.assertIn('call 0x10925a0', text)
  self.assertIn('lea rcx, [rsi + 0x78]', text)
  self.assertIn('call 0x10924c0', text)
  self.assertIn('call 0x1092790', text)

 def test_live_stock_has_train_not_infantry_and_type_index_15(self):
  ev=json.loads((ROOT/'research/t174_alloc_and_stock_live.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['pid'],26976)
  self.assertEqual(ev['hour_tick'],60759371)
  self.assertEqual(ev['infantry_type']['name'],'infantry_equipment')
  self.assertEqual(ev['infantry_type']['plus598_i32'],15)
  names=[r['name'] for r in ev['stock_production_plus200']['rows']]
  self.assertEqual(names,['train_equipment'])
  self.assertEqual(ev['stock_production_plus200']['rows'][0]['amount'],5)
  self.assertNotIn('infantry_equipment', names)
  self.assertEqual(ev['need']['rows'][0]['amount'],80)
  self.assertEqual(ev['logistics']['plus20_is_country'],True)
  self.assertEqual(ev['mode_objects'][0]['class'],'CLoopHistory')

 def test_still_not_emitted_as_demanded_or_affected(self):
  cap=json.loads((ROOT/'research/t171_live_capture.json').read_text(encoding='utf-8'))
  eq=cap['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(cap['complete_input'])

if __name__=='__main__':
 unittest.main()
