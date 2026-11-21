import ast, copy, json, unittest
from pathlib import Path
import t219_captured_equipment_replay as m
Q=Path(__file__).parent
class EquipmentReplayTests(unittest.TestCase):
 def setUp(self):
  self.docs={n:json.loads((Q/n).read_text())for n in {r['file']for r in m.CONTRACT.values()}}
  self.live=self.docs['t219_live_equipment_cache_and_types.json']
 def typ(self,name='infantry_equipment'):
  return next(t for t in self.live['types']if t['name']==name)
 def reject(self):
  with self.assertRaises((ValueError,KeyError,TypeError)):m.replay(self.docs)
 def test_01_positive_infantry(self):self.assertEqual(m.replay(self.docs)['infantry_equipment']['demanded'],10015)
 def test_02_positive_artillery(self):self.assertEqual(m.replay(self.docs)['artillery_equipment']['demanded'],147)
 def test_03_positive_support(self):self.assertEqual(m.replay(self.docs)['support_equipment']['demanded'],121)
 def test_04_positive_light_tank_chassis(self):self.assertEqual(m.replay(self.docs)['light_tank_chassis']['demanded'],2324)
 def test_05_rejects_stale_daily_cache(self):self.live['caches'][1]['values_raw'][15]+=1;self.reject()
 def test_06_negative_cached_stock_clamped_not_subtracted(self):
  r=m.replay(self.docs)['infantry_equipment'];self.assertEqual(r['native_current_raw'],0);self.assertEqual(self.live['caches'][0]['values_raw'][15],-75000)
 def test_07_rejects_missing_cache(self):self.live['caches'].pop();self.reject()
 def test_08_rejects_partial_cache(self):self.live['caches'][1]['values_raw'].pop();self.reject()
 def test_09_rejects_dense_index_alias(self):self.typ()['dense_index_598']=4;self.reject()
 def test_10_rejects_duplicate_type_name(self):self.typ()['name']='artillery_equipment';self.reject()
 def test_11_rejects_inherited_scope(self):self.typ()['base_type_ptr']='0x1234';self.reject()
 def test_12_rejects_bit31_special(self):self.typ()['own_flags_5a0']|=1<<31;self.reject()
 def test_13_rejects_vehicle_special(self):self.typ()['special_44b']=1;self.reject()
 def test_14_rejects_convoy_stock_path(self):self.typ()['extra_flags_5a8']=1;self.reject()
 def test_15_rejects_main_type_gate_false(self):self.typ()['own_flags_5a0']=0;self.reject()
 def test_16_rejects_nonempty_deployment(self):self.live['components']['deployment']['count']=1;self.reject()
 def test_17_rejects_nonempty_resources(self):self.live['components']['countryresources']['count']=1;self.reject()
 def test_18_rejects_nonempty_occupation(self):self.live['components']['occupation']['count']=1;self.reject()
 def test_19_rejects_nonempty_operations(self):self.live['components']['operations']['count']=1;self.reject()
 def test_20_rejects_nonempty_logistics(self):self.live['components']['logistics']['count']=1;self.reject()
 def test_21_rejects_changed_tick(self):self.live['after']['hour_tick']+=1;self.reject()
 def test_22_rejects_open_gate(self):self.live['before']['markers']['safe_land_tool_gate.OPEN']=True;self.reject()
 def test_23_rejects_native_byte_change(self):
  r=next(iter(m.CONTRACT.values()));f=self.docs[r['file']]['flows']['0x1409810'];f['raw_hex']='00'+f['raw_hex'][2:];self.reject()
 def test_24_rejects_unresolved_edge(self):
  self.docs['t219_equipment_type_and_cache_flows.json']['flows']['0x1409810']['unresolved_edges']=[{'reason':'synthetic'}];self.reject()
 def test_25_rejects_negative_request(self):self.live['requests'][0]['need'][0]['amount_raw']=-1;self.reject()
 def test_26_rejects_boolean_request(self):self.live['requests'][0]['need'][0]['amount_raw']=True;self.reject()
 def test_27_rejects_overrange_request(self):self.live['requests'][0]['need'][0]['amount_raw']=m.MAXIMUM+1;self.reject()
 def test_28_rejects_duplicate_request_type(self):
  r=self.live['requests'][0]['need'];r.append(copy.deepcopy(r[0]));self.reject()
 def test_29_rejects_mixed_session_code(self):
  self.docs['t219_scoped_demand_leaf_controls.json']['before']['pid']=6496;self.reject()
 def test_30_rejects_fractional_demand(self):
  row=next(r for req in self.live['requests']for r in req['need']if r['equipment_type']=='infantry_equipment');row['amount_raw']+=1;self.reject()
 def test_31_flags_normalization_precedence(self):
  self.assertEqual(m.normalize(0x40|0x80|0x100|1),0x40);self.assertEqual(m.normalize(0x80|0x100|1),0x80);self.assertEqual(m.normalize(0x100|1),0x100)
 def test_32_saturation_bounds(self):
  self.assertEqual(m.capped(m.MAXIMUM+1),m.MAXIMUM);self.assertEqual(m.capped(-m.MAXIMUM-1),-m.MAXIMUM);self.assertEqual(m.capped(17),17)
 def test_33_scope_excludes_motorized_air_convoy_train(self):self.assertEqual(set(m.replay(self.docs)),set(m.SCOPE))
 def test_34_replay_has_no_process_or_production_import(self):
  tree=ast.parse((Q/'t219_captured_equipment_replay.py').read_text());names={n.name for x in ast.walk(tree)if isinstance(x,ast.Import)for n in x.names};self.assertEqual(names,{'hashlib'})
 def test_35_real_rejection_not_reclassified_as_stockpile(self):
  rejects=[x['name']for x in self.live['stockpool_raw_diagnostic_ONLY']if x['production_parser_rejects_range_or_quantity']];self.assertEqual(set(rejects),{'artillery_equipment','infantry_equipment','support_equipment'});self.assertEqual(len(self.live['requests']),113)
if __name__=='__main__':unittest.main()
