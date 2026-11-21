import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))

class Tests(unittest.TestCase):
 def test_d71810_is_deployment_daily_and_calls_d71b60(self):
  text=(ROOT/'research/_t177_clip_d71810.txt').read_text(encoding='utf-8')
  self.assertIn('0xd7183a  lea r8, [rip + 0x1c6b017]', text)
  # dest 0xd71841+0x1c6b017 = 0x29dc858 "deployment.daily"
  self.assertEqual(0xd71841+0x1c6b017, 0x29dc858)
  self.assertIn('call 0xd71b60', text)
  self.assertIn('mov rsi, rdx', text)

 def test_72f220_passes_country_f78_to_d71810(self):
  text=(ROOT/'research/_t177_win_f78_0x72f220_0x72f3be.txt').read_text(encoding='utf-8')
  self.assertIn('mov r9, qword ptr [rdi + 0xfd0]', text)
  self.assertIn('mov r8, qword ptr [rdi + 0xf80]', text)
  self.assertIn('mov rdx, qword ptr [rdi + 0xf78]', text)
  self.assertIn('mov rcx, qword ptr [rdi + 0xf70]', text)
  self.assertIn('call 0xd71810', text)

 def test_d71b60_enumerates_production_plus200_and_calls_slot2_with_qty(self):
  text=(ROOT/'research/_t177_clip_d71b60.txt').read_text(encoding='utf-8')
  self.assertIn('mov rsi, qword ptr [rax + 0xf68]', text)
  self.assertIn('lea rcx, [rsi + 0x200]', text)
  self.assertIn('call 0x1095760', text)
  self.assertIn('mov r15, qword ptr [rdi + r15]', text)
  self.assertIn('mov rdi, qword ptr [rdi + rax + 8]', text)
  self.assertIn('test rdi, rdi', text)
  self.assertIn('mov rax, qword ptr [rbp + 0x1008]', text)
  self.assertIn('call 0xd6f140', text)
  self.assertIn('mov r9, rdi', text)
  self.assertIn('mov r8, r15', text)
  self.assertIn('0xd723b6  call qword ptr [rax + 0x10]', text)
  self.assertIn('mov rdi, qword ptr [rax]', text)

 def test_d6f140_appends_if_slot1_want_positive(self):
  text=(ROOT/'research/_t177_clip_d6f140.txt').read_text(encoding='utf-8')
  self.assertIn('call qword ptr [rax + 8]', text)
  self.assertIn('mov qword ptr [rbx + 0x10], r8', text)
  self.assertIn('test r8, r8', text)
  self.assertIn('jle 0xd6f221', text)
  self.assertIn('mov qword ptr [rax + rcx*8], rbx', text)

 def test_1095760_copies_present_type_qty_rows(self):
  text=(ROOT/'research/_t177_clip_1095760.txt').read_text(encoding='utf-8')
  self.assertIn('movsxd r15, dword ptr [r13 + 0x2c]', text)
  self.assertIn('mov rcx, qword ptr [r13 + 0x20]', text)
  self.assertIn('mov rax, qword ptr [rcx + rbp + 8]', text)
  self.assertIn('add rbp, 0x10', text)

 def test_1eae60_is_gamestate_daily_and_calls_72f220(self):
  head=(ROOT/'research/_t177_clip_1eae60.txt').read_text(encoding='utf-8')
  self.assertIn('0x1eae84  lea rdx, [rip + 0x25b5a45]', head)
  self.assertEqual(0x1eae8b+0x25b5a45, 0x27a08d0)
  ev=json.loads((ROOT/'research/t177_d71810_e8.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['72f220']['funcs'],['0x1eae60'])
  self.assertEqual(ev['d71810']['funcs'],['0x72f220'])

 def test_live_country_status_classes(self):
  live=json.loads((ROOT/'research/t177_country_statuses_live.json').read_text(encoding='utf-8'))
  self.assertEqual(live['f70']['class'],'CDeploymentStatus')
  self.assertEqual(live['f68_production']['class'],'CProductionStatus')
  self.assertEqual(live['f78_reinforcement']['class'],'CReinforcementStatus')
  self.assertEqual(live['f78_reinforcement']['ptr'],'0x26c49c0c140')
  self.assertEqual(live['f80']['class'],'CArmyUpgradesStatus')
  self.assertEqual(live['fd0']['class'],'CCountryOccupationStatus')

 def test_still_not_emitted_as_demanded_or_affected(self):
  cap=json.loads((ROOT/'research/t171_live_capture.json').read_text(encoding='utf-8'))
  eq=cap['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(cap['complete_input'])

if __name__=='__main__':
 unittest.main()
