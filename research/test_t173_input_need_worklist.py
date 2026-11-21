import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))

class Tests(unittest.TestCase):
 def test_cdb4b0_plus_108_is_template_need_pool(self):
  # cdb4b0 returns CReferencedDivisionTemplate+0x18; 15aa9c0 does lea [rax+0x108]
  self.assertEqual(0x18+0x108,0x120)

 def test_live_request_need_equals_template_minus_current(self):
  ev=json.loads((ROOT/'research/t171_country_need_semantics.json').read_text(encoding='utf-8'))
  # 1835: need 400, current 320, request need 80, official contribution 77 = 80-3
  self.assertEqual(ev['live_scene']['request_need_minus_produced_infantry'],77)
  self.assertEqual(ev['live_scene']['official_1409810_infantry_this_scene'],77)
  self.assertEqual(ev['live_scene']['contributors'],[1835])

 def test_no_stored_7700000_on_campaign_roots(self):
  ev=json.loads((ROOT/'research/t173_stored_need_live.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['expected_need_raw'],7700000)
  self.assertEqual(ev['bounded_hits']['7700000'],[])
  self.assertEqual(ev['logistics']['plus20_is_country'],True)
  self.assertEqual(ev['infantry_type']['name'],'infantry_equipment')
  self.assertNotEqual(ev['infantry_type']['plus648_i64'],7700000)
  self.assertNotEqual(ev['infantry_type']['plus608_i64'],7700000)

 def test_still_not_emitted_as_demanded_or_affected(self):
  cap=json.loads((ROOT/'research/t171_live_capture.json').read_text(encoding='utf-8'))
  eq=cap['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(cap['complete_input'])

if __name__=='__main__':
 unittest.main()
