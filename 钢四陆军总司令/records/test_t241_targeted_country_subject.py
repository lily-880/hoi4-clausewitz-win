# Unique t241 offline scenarios; native code never executed.
import unittest,json,hashlib,io
from pathlib import Path
Q=Path(__file__).resolve().parent
load=lambda n:json.loads((Q/(n+'.json')).read_text(encoding='utf-8'))
C=load('t241_country_lookup_contract');B=load('t241_country_bucket_layout');T=load('t241_targeted_subject_controls');G=load('t241_fresh_guard');F={**C['functions'],**B['functions']};L={e['requested_tag']:e for e in T['targeted_lookups']};POS,NEG=T['directional_pairs']
a=lambda f:'\n'.join(F[f]['asm'])
def fnv(s):
 h=0x811c9dc5
 for b in s.encode('ascii'):h=((h^b)*0x1000193)&0xffffffff
 return h
class Targeted(unittest.TestCase):
 def test_01_fnv_exact_constants_length_loop(self):
  s=a('0x763e10')
  for v in ['0x811c9dc5','0x1000193','xor ecx, r9d','[rdx + 0x10]','sub rdx, 1']:self.assertIn(v,s)
 def test_02_input_small_string_or_heap_branch(self):
  s=a('0x763e10');self.assertIn('[rdx + 0x18], 0xf',s);self.assertIn('mov r8, qword ptr [rdx]',s);self.assertIn('jbe 0x763e30',s)
 def test_03_lookup_map_receiver_and_pair_result(self):
  s=a('0x763e10');self.assertIn('lea rcx, [rbx + 0x48]',s);self.assertIn('call 0x1d5170',s);self.assertIn('mov rax, qword ptr [rax + 8]',s);self.assertIn('mov eax, dword ptr [rax + 0x30]',s)
 def test_04_notfound_sentinel_minus_one_not_arbitrary_node(self):
  s=a('0x763e10');self.assertIn('cmp rax, qword ptr [rbx + 0x50]',s);self.assertIn('mov eax, 0xffffffff',s)
 def test_05_reference_array_index_bound_and_invalid_path_not_called(self):
  s=a('0x763ea0')
  for x in ['test edx, edx','js 0x763ec3','cmp edx, dword ptr [rcx + 0x3c]','jge 0x763ec3','[rcx + 0x30]','[rax + rdx*4]','int3']:self.assertIn(x,s)
  self.assertIn('outside of array',{v['text'] for v in F['0x763ea0']['literals']}.pop())
 def test_06_bucket_mask_stride_and_sentinel(self):
  s=a('0x1d5170')
  for x in ['[rcx + 0x30]','and rbp, r9','shl rbp, 4','[rcx + 0x18]','[rcx + 8]']:self.assertIn(x,s)
  self.assertEqual(T['mask'],511);self.assertEqual(T['dictionary_count'],440)
 def test_07_bucket_last_to_first_inclusive_previous_link(self):
  s=a('0x1d5170')
  for x in ['mov rbx, qword ptr [rbp + 8]','mov rbp, qword ptr [rbp]','cmp rbx, rbp','mov rbx, qword ptr [rbx + 8]']:self.assertIn(x,s)
  source=(Q/'t241_targeted_subject_controls.py').read_text();self.assertIn('len(seen)<32',source);self.assertIn('node not in seen',source)
 def test_08_exact_string_length_and_comparator_zero_branch(self):
  s=a('0x1d5170')
  for x in ['[rbx + 0x28], 0xf','lea rdx, [rbx + 0x10]','cmp rsi, rax','call 0x26078d0','test eax, eax','je 0x1d5210']:self.assertIn(x,s)
 def test_09_failed_polymorphic_assumption_preserved(self):
  f=load('t241_country_bucket_contract_failure1');self.assertEqual(f['exit_code'],1);self.assertFalse(f['completed_artifact']);self.assertFalse(B['polymorphic_class_claim']);self.assertIsNone(B['lookup_root_class']);self.assertEqual(B['lookup_root_rva'],'0x33df288');self.assertEqual(len(bytes.fromhex(B['lookup_root_header_hex'])),0xa0)
 def test_10_four_target_hashes_independently_recomputed(self):
  self.assertEqual(list(L),['MAN','JAP','SOV','QZQ'])
  for t,e in L.items():self.assertEqual(int(e['fnv1a32'],16),fnv(t));self.assertEqual(e['bucket_index'],fnv(t)&511)
 def test_11_live_named_country_identity_bridge(self):
  for name,index in [('MAN',113),('JAP',48),('SOV',3)]:
   e=L[name]['result'];self.assertEqual((e['dictionary_index'],e['country_ref_raw'],e['canonical_index'],e['current_country_tag']),(index,index,index,name))
 def test_12_genuine_lookup_negative_nonempty_collision_bucket(self):
  self.assertEqual(L['QZQ']['visited_bucket_keys'],['RHD']);self.assertIsNone(L['QZQ']['result']);self.assertNotEqual(fnv('QZQ'),fnv('RHD'));self.assertEqual(fnv('QZQ')&511,fnv('RHD')&511);self.assertEqual(sum(len(e['visited_bucket_keys']) for e in L.values()),4)
 def test_13_live_forward_parent_plus_puppet_level_positive(self):
  self.assertEqual((POS['source_named_tag'],POS['target_named_tag']),('MAN','JAP'));self.assertEqual((POS['source_parent_ref'],POS['target_country_ref']),(48,48));self.assertTrue(POS['source_level_present']);self.assertTrue(POS['source_definition_present']);self.assertEqual(POS['source_puppet_flag'],1);self.assertTrue(POS['derived_native_puppet_of_projection'])
 def test_14_live_forward_dependency_type_and_direction_positive(self):
  self.assertEqual(POS['relation_dependency_inputs'],dict(present=True,type_token=0x30d1,dependency_country_ref=48,relation_country_ref=48));self.assertTrue(POS['derived_native_subject_of_projection'])
 def test_15_live_reverse_parent_and_level_negative(self):
  self.assertEqual((NEG['source_named_tag'],NEG['target_named_tag']),('JAP','MAN'));self.assertEqual(NEG['source_parent_ref'],0);self.assertFalse(NEG['source_level_present']);self.assertFalse(NEG['source_definition_present']);self.assertEqual(NEG['source_puppet_flag'],0);self.assertFalse(NEG['derived_native_puppet_of_projection'])
 def test_16_live_reverse_record_present_same_token_still_negative(self):
  self.assertEqual(NEG['relation_dependency_inputs'],dict(present=True,type_token=0x30d1,dependency_country_ref=48,relation_country_ref=113));self.assertFalse(NEG['derived_native_subject_of_projection']);self.assertNotEqual(48,113)
 def test_17_positive_subject_not_subject_of_player(self):
  self.assertNotEqual(POS['source_parent_ref'],L['SOV']['result']['country_ref_raw']);self.assertEqual(L['SOV']['result']['canonical_index'],G['before']['country_index']);self.assertNotEqual(POS['target_canonical_index'],G['before']['country_index'])
class Shared(unittest.TestCase):
 def test_18_captured_native_raw_hashes_and_pin_union(self):
  old=load('t241_prior_all_native_pins');allp=load('t241_all_native_pins');self.assertEqual((len(old),len(allp)),(172,175));self.assertTrue(old.items()<=allp.items())
  for f in F.values():
   raw=bytes.fromhex(f['raw_hex']);self.assertEqual(len(raw),f['window_size']);self.assertEqual(hashlib.sha256(raw).hexdigest(),f['sha256']);self.assertEqual(int(f['pdata'][1],16)-int(f['pdata'][0],16),len(raw));self.assertEqual(f['window_start'],f['pdata'][0]);self.assertEqual(allp[f['window_start']+'/'+str(len(raw))]['sha256'],f['sha256']);self.assertEqual(f['unresolved_edges'],[])
 def test_19_session_fingerprint_and_inventory(self):
  for d in [C,B,T,G]:self.assertEqual(d['before'],d['after']);self.assertEqual(d['before'],G['before'])
  b=G['before'];self.assertEqual((b['pause'],b['speed_slot'],b['hour_tick']),(1,0,60781105));self.assertFalse(any(b['markers'].values()));self.assertTrue(G['safe']);self.assertEqual(G['rechecked_prior_native_windows'],172);self.assertEqual(G['production_baseline_fields'],51);self.assertEqual(len(G['production_hashes']),4)
  self.assertEqual(hashlib.sha256(Path('/workspace/hoi4-docs-latest/态势信息读取能力清单.md').read_bytes()).hexdigest(),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
 def test_20_no_visibility_or_raw_field_promotion(self):
  self.assertEqual(T['native_calls'],0);self.assertEqual(T['new_visibility_checks'],0);self.assertFalse(T['schema_visible_relation_emitted']);self.assertEqual(T['promotions'],[])
  for p in T['directional_pairs']:self.assertTrue(p['projection_not_raw_schema_field'])
if __name__=='__main__':
 loader=unittest.TestLoader();suite=unittest.TestSuite([loader.loadTestsFromTestCase(Targeted),loader.loadTestsFromTestCase(Shared)]);ids=[t.id() for sub in suite for t in sub];out=io.StringIO();r=unittest.TextTestRunner(stream=out,verbosity=2).run(suite);report=dict(successful=r.wasSuccessful(),unique_methods=len(set(ids)),total_test_invocations=r.testsRun,targeted_methods=17,shared_methods=3,suite_starts=1,completed_suite_runs=1,failures=len(r.failures),errors=len(r.errors),collection_failures=0,method_ids=ids,output=out.getvalue());(Q/'t241_regression_attempt1.json').write_text(json.dumps(report,indent=2)+'\n');print(out.getvalue());raise SystemExit(not r.wasSuccessful())
