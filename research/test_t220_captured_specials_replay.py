import ast,copy,json,unittest
from pathlib import Path
import t220_captured_specials_replay as m
Q=Path(__file__).parent
class SpecialReplayTests(unittest.TestCase):
 def setUp(self):
  self.native=json.loads((Q/'t220_bound_special_native_flows.json').read_text());self.mapping=json.loads((Q/'t220_country_logistics_mapping_and_counts.json').read_text());self.sample=json.loads((Q/'t220_train_motor_independent_positive_samples.json').read_text());self.join=json.loads((Q/'t220_variant_handle_crosscheck.json').read_text())
 def runproof(self):return m.replay(self.native,self.mapping,self.sample,self.join)
 def reject(self):
  with self.assertRaises((ValueError,KeyError,TypeError)):self.runproof()
 def test_01_train_83_minus15_is_available68_not_demand15(self):
  r=self.runproof()['train_equipment'];self.assertEqual((r['owned_counter'],r['count_operand'],r['native_current_raw'],r['demanded']),(83,15,6800000,0))
 def test_02_positive_motor_demand1278(self):self.assertEqual(self.runproof()['motorized_equipment']['demanded'],1278)
 def test_03_train_worklist_positive_1_1_5_1_7(self):self.assertEqual([x['integer_amount']for x in self.sample['worklist_stride48']],[1,1,5,1,7]);self.runproof()
 def test_04_positive_variant83_and_exact_handle_join(self):self.assertEqual(self.join['rows'][0]['variant_handle_plus8_raw'],6274947219526);self.runproof()
 def test_05_rejects_wrong_mapping(self):self.sample['mapping']['mapped_index']=4;self.reject()
 def test_06_rejects_mapping_out_of_bounds(self):self.mapping['map']['mapped_index']=9999;self.reject()
 def test_07_rejects_foreign_parent(self):self.sample['mapping']['country_backlink']='0x123';self.reject()
 def test_08_rejects_wrong_child(self):self.sample['mapping']['child80_ptr']='0x123';self.reject()
 def test_09_rejects_wrong_supply_class(self):self.mapping['map']['returned_class']='.?AVCCountry@@';self.reject()
 def test_10_rejects_corrupt_raw_worklist(self):self.sample['worklist_stride48'][0]['raw_hex']='00'*48;self.reject()
 def test_11_rejects_mismatched_train_accumulator(self):self.sample['counters']['train_operand_child140']=16;self.reject()
 def test_12_rejects_mismatched_train_owned_counter(self):self.sample['counters']['train_total_plus110']=82;self.reject()
 def test_13_rejects_wrong_variant_handle(self):self.join['rows'][0]['variant_handle_plus8_raw']+=1;self.reject()
 def test_14_rejects_fractional_owned_variant(self):self.sample['owned_train_variants'][0]['raw_quantity']+=1;self.reject()
 def test_15_rejects_wrong_variant_train_predicate(self):self.sample['owned_train_variants'][0]['flags_effective']=8;self.reject()
 def test_16_rejects_pool_quantity_mismatch(self):self.sample['train_pool_stride24'][0]['integer_amount_plus8']=82;self.reject()
 def test_17_rejects_duplicate_pool_handle(self):self.sample['train_pool_stride24'].append(copy.deepcopy(self.sample['train_pool_stride24'][0]));self.reject()
 def test_18_rejects_stale_train_balance(self):self.sample['types']['train_equipment']['cache16_raw']+=100000;self.reject()
 def test_19_rejects_stale_motor_balance(self):self.sample['types']['motorized_equipment']['cache16_raw']+=100000;self.reject()
 def test_20_rejects_cleared_motor_special_flag(self):self.sample['types']['motorized_equipment']['special_44b']=0;self.reject()
 def test_21_rejects_wrong_motor_rawflag(self):self.sample['types']['motorized_equipment']['own_flags']=0x10;self.reject()
 def test_22_rejects_nonempty_extra_component(self):self.sample['components']['deployment']['count']=1;self.reject()
 def test_23_rejects_changed_tick(self):self.sample['after']['hour_tick']+=1;self.reject()
 def test_24_rejects_open_gate(self):self.sample['before']['markers']['safe_land_tool_gate.OPEN']=True;self.reject()
 def test_25_rejects_wrong_build(self):self.mapping['version']='other';self.reject()
 def test_26_rejects_changed_native_counter_writer(self):self.native['0x12be8f0']['flow']['raw_hex']='00';self.reject()
 def test_27_rejects_unclosed_native_counter_writer(self):self.native['0x12b8e40']['flow']['unresolved_edges']=[{'reason':'synthetic'}];self.reject()
 def test_28_rejects_negative_counter(self):self.sample['counters']['motor_operand_c8']=-1;self.reject()
 def test_29_rejects_boolean_counter(self):self.sample['counters']['motor_total_plus138']=False;self.reject()
 def test_30_synthetic_train_shortfall5_not_total15(self):self.assertEqual(m.special(0,1000000,15,10,True),(500000,0))
 def test_31_synthetic_train_current_clamp(self):self.assertEqual(m.special(0,1000000,15,10,True)[1],0)
 def test_32_synthetic_motor_negative_not_train_clamp(self):self.assertEqual(m.special(0,0,0,3,False),(-300000,300000))
 def test_33_replay_has_no_process_import(self):
  tree=ast.parse((Q/'t220_captured_specials_replay.py').read_text());names={n.name for x in ast.walk(tree)if isinstance(x,ast.Import)for n in x.names};self.assertEqual(names,{'hashlib','struct'})
 def test_34_rejects_inherited_type_scope(self):self.sample['types']['train_equipment']['base_ptr']='0x1';self.reject()
if __name__=='__main__':unittest.main()
