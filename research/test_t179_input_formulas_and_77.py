import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))

class Tests(unittest.TestCase):
 def test_1409810_callers_are_ui_or_script_not_stored_total(self):
  ev=json.loads((ROOT/'research/t179_1409810_callers.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['e8']['1409810']['count'],11)
  funcs=set(ev['e8']['1409810']['funcs'])
  self.assertEqual(len(funcs),10)
  conc=json.loads((ROOT/'research/t179_1409810_no_stored_total.json').read_text(encoding='utf-8'))
  self.assertTrue(set(conc['classification']).issuperset(funcs))
  self.assertTrue(conc['all_ui_or_script_or_known_ui_cache'])
  self.assertTrue(conc['conclusion'].startswith('No campaign-stored'))

 def test_52df40_is_script_foreach_not_status_store(self):
  ev=json.loads((ROOT/'research/t179_1409890_callers.json').read_text(encoding='utf-8'))
  strs=[s['s'] for s in ev['52df40']['strings']]
  self.assertTrue(any('Infinite cycle in event FROM scope' in s for s in strs))
  self.assertTrue(any('Parallel]ForEach' in s for s in strs))
  # the only lock-add site
  wins=json.loads((ROOT/'research/t179_1409810_callers.json').read_text(encoding='utf-8'))['windows']
  lock=[w for w in wins if w['post_has_lock_add']]
  self.assertEqual([w['func'] for w in lock],['0x52df40'])

 def test_140ba10_is_postdaily_logistics_diff_not_stored_77(self):
  text=(ROOT/'research/_t179_clip_140ba10.txt').read_text(encoding='utf-8')
  self.assertIn('call 0x1409890', text)
  self.assertIn('call 0x14080c0', text)
  self.assertIn('call 0x15b3220', text)
  ev=json.loads((ROOT/'research/t179_1409890_callers.json').read_text(encoding='utf-8'))
  row=next(w for w in ev['1409890_windows'] if w['func']=='0x140ba10')
  self.assertIn('logistics.postdailythreaded', row['strings'])
  conc=json.loads((ROOT/'research/t179_1409810_no_stored_total.json').read_text(encoding='utf-8'))
  self.assertTrue(conc['logistics_postdailythreaded']['live_logistics_e48_is_80_not_77'])

 def test_bounded_scan_has_no_stored_77_fixed(self):
  ev=json.loads((ROOT/'research/t179_bounded_77_scan.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['need77_fixed'],7700000)
  self.assertEqual(ev['hits_distinctive'],[])
  # production present rows still only train 5
  rows=[o for o in ev['objects'] if o.get('label')=='pool_hdr20']
  self.assertEqual(len(rows),1)
  self.assertFalse(rows[0]['has_77'])
  self.assertEqual(rows[0]['rows'][0]['qty_int'],5.0)

 def test_need_and_produced_formulas_recorded_not_promoted(self):
  f=json.loads((ROOT/'research/t179_need_produced_formulas.json').read_text(encoding='utf-8'))
  self.assertIn('CReferencedDivisionTemplate+0x120 minus CArmy+0x348', f['need']['unit_remaining'])
  self.assertIn('1409890', f['need']['official_country_1409810'])
  self.assertIn('official 1409810 infantry = 77', f['need']['this_scene'])
  self.assertIn('give = min(max(0, need - produced), offered)', f['produced']['formula'])
  self.assertIn('pre-daily', f['produced']['formula'].lower())
  self.assertIn('min(need, current stock)', f['produced']['not'])
  self.assertIn('[1835]', f['not_promoted']['affected_unit_ids'])

 def test_still_not_emitted_as_demanded_or_affected(self):
  cap=json.loads((ROOT/'research/t171_live_capture.json').read_text(encoding='utf-8'))
  eq=cap['observation']['world']['shortages']['equipment']
  self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
  self.assertNotIn('demanded',eq[0])
  self.assertNotIn('affected_unit_ids',eq[0])
  self.assertFalse(cap['complete_input'])

 def test_adjacency_stride48_empirical_not_promoted(self):
  ev=json.loads((ROOT/'research/t179_adjacency_stride48_empirical.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['stride_bytes'],48)
  self.assertEqual(ev['target_offset'],8)
  self.assertEqual(ev['reciprocal_own_edges'], ev['internal_own_edges'])
  self.assertGreaterEqual(ev['reciprocal_own_edges'],20)
  self.assertEqual(ev['self_edges'],0)
  self.assertEqual(ev['plausible_ids'], ev['edges'])
  self.assertTrue(ev['status'].endswith('not_promoted'))
  self.assertIn('Do not emit', ev['caveat'])

if __name__=='__main__':
 unittest.main()
