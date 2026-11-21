# t242 independent offline checks, no process APIs/native calls.
import unittest,json,hashlib,io,struct
from pathlib import Path
Q=Path(__file__).resolve().parent
load=lambda n:json.loads((Q/(n+'.json')).read_text(encoding='utf-8'))
N=load('t242_named_allied_consumers');T=load('t242_targeted_faction_controls');I=load('t242_isolation_receiver_methods');S=load('t242_isolation_loader_switch_offline');L=load('t242_loader_literal_receiver');G=load('t242_fresh_guard');F={**N['functions'],**I['functions']};a=lambda f:'\n'.join(F[f]['asm']);resolved='\n'.join(S['resolved_asm'])
class Targeted(unittest.TestCase):
 def test_01_named_faction_consumer_not_generic_friend_claim(self):
  self.assertIn('TRIGGER_IS_IN_FACTION_WITH',{x['text'] for x in N['names']});self.assertIn('TRIGGER_IS_IN_FACTION_WITH',{x['text'] for x in F['0x43eb90']['literals']});self.assertNotIn('TRIGGER_IS_ALLIED_WITH',{x['text'] for x in N['names']})
 def test_02_full_trigger_interface_binding(self):
  self.assertEqual(N['tables'],[dict(tooltip='0x43eb90',tooltip_slot=21,vtable_rva='0x280f220',class_name='.?AVCIsInFactionWithTrigger@@',col_offset=0,evaluator_slot=22,evaluator_rva='0x3f90f0')]);slots=T['actual_extended_interface_slots'];self.assertEqual(slots[2],dict(index=23,rva='0x1443990',in_text=True));self.assertFalse(slots[3]['in_text'])
 def test_03_bilateral_scope_and_dynamic_target(self):
  s=a('0x3f90f0')
  for x in ['[rax + 0xb8]','[rbx + 8]','call 0xc07bf0','[rax + 0xf88]']:self.assertIn(x,s)
 def test_04_two_nonnull_preconditions_not_null_equality(self):
  s=a('0x3f90f0');self.assertEqual(s.count('cmp qword ptr [rcx + 0x2d8], 0'),2);self.assertEqual(s.count('je 0x3f9180'),2);self.assertIn('3f9180 xor al, al',s)
 def test_05_only_nonnull_shared_pointer_returns_true(self):
  s=a('0x3f90f0');self.assertIn('mov rax, qword ptr [rcx + 0x2d8]',s);self.assertIn('cmp qword ptr [rbx + 0x2d8], rax',s);self.assertIn('sete al',s)
 def test_06_bounded_three_named_live_controls(self):
  self.assertEqual([x['requested_tag'] for x in T['targeted_lookups']],['SOV','MON','JAP']);self.assertEqual(sum(len(x['visited_bucket_keys']) for x in T['targeted_lookups']),3)
  for e,index in zip(T['targeted_lookups'],[3,69,48]):self.assertEqual((e['result']['canonical_index'],e['result']['current_country_tag']),(index,e['requested_tag']))
 def test_07_live_sov_mon_two_nulls_are_false(self):
  for p in T['directional_pairs'][:2]:self.assertFalse(p['source_nonnull']);self.assertFalse(p['target_nonnull']);self.assertFalse(p['derived_native_is_in_faction_with_projection']);self.assertEqual(p['source_faction_pointer'],p['target_faction_pointer'])
 def test_08_live_jap_nonnull_does_not_make_sov_friendly(self):
  for p in T['directional_pairs'][2:]:self.assertNotEqual(p['source_nonnull'],p['target_nonnull']);self.assertFalse(p['derived_native_is_in_faction_with_projection'])
  self.assertTrue(T['current_native_inputs']['JAP']['faction_nonnull'])
 def test_09_four_directed_two_unordered_no_positive(self):
  pairs=T['directional_pairs'];self.assertEqual([(p['source'],p['target']) for p in pairs],[('SOV','MON'),('MON','SOV'),('SOV','JAP'),('JAP','SOV')]);self.assertEqual(len({frozenset([p['source'],p['target']]) for p in pairs}),2);self.assertFalse(any(p['derived_native_is_in_faction_with_projection'] for p in pairs))
 def test_10_distinct_field_pivot_without_visible_assumption(self):
  self.assertEqual(I['independent_pivot_field'],'world.own_units.supply.isolated');self.assertEqual(I['live_unit_samples'],0);self.assertEqual(T['new_visibility_checks'],0);self.assertFalse(T['schema_visible_relation_emitted'])
 def test_11_secondary_army_receiver_not_separate_class(self):
  self.assertEqual((I['class_name'],I['col_offset']),('.?AVCArmy@@',16));self.assertEqual(I['slots'],{'0x10':'0xced2e0','0x20':'0xce95a0'});self.assertEqual(I['vtable_rva'],'0x29d6f78')
 def test_12_persistence_body_not_lifecycle_execution(self):
  s=a('0xced2e0');self.assertIn('call 0xf4ca30',s);self.assertIn('call 0x2546250',s);self.assertEqual(F['0xced2e0']['unresolved_edges'],[])
 def test_13_original_loader_partial_evidence_retained(self):
  self.assertEqual(F['0xce95a0']['unresolved_edges'],[dict(address='0xce97cf',reason='indirect jump',operand='rcx')]);self.assertIn('Error while loading OOB: ',{v['text'] for v in F['0xce95a0']['literals']});self.assertEqual(S['source_native_sha256'],F['0xce95a0']['sha256'])
 def test_14_exact_two_level_switch_bound_and_closure(self):
  f=F['0xce95a0'];raw=bytes.fromhex(f['raw_hex']);start=int(f['window_start'],16);idx=list(raw[0xcea1b8-start:0xcea1b8-start+75]);self.assertEqual(idx,S['byte_indices']);self.assertEqual(sorted(set(idx)),list(range(7)));targets=sorted({hex(struct.unpack_from('<I',raw,0xcea19c-start+i*4)[0]) for i in idx});self.assertEqual(targets,S['targets']);self.assertEqual(S['remaining_unresolved'],[]);self.assertEqual(S['input_upper_bound'],74);self.assertEqual(len(S['resolved_asm']),653)
 def test_15_false_plus2e_writer_is_new_string_allocation(self):
  s=a('0xce95a0')
  for x in ['ce9a0e mov ecx, 0x30','ce9a13 call 0x25a01dc','ce9a18 mov rcx, rax','ce9a6b mov byte ptr [rcx + 0x2e], al','ce9a6e mov byte ptr [rcx + 0x2f], sil']:self.assertIn(x,s)
  self.assertEqual(L['exact_constant']['ascii'],'Army refers to a non existing division template');self.assertEqual(L['exact_constant']['window_size'],47)
 def test_16_explicit_complete_receiver_adjustment_not_offset_inference(self):
  self.assertIn('lea rcx, [rdi - 0x10]',resolved);self.assertIn('lea rdx, [rdi + 0x29f]',resolved);self.assertEqual(0x29f+I['col_offset'],0x2af)
 def test_17_next_base_parser_is_opaque_not_closed_writer(self):
  self.assertIn('cea036 mov rcx, rdi',resolved);self.assertIn('cea039 call 0xc58600',resolved);self.assertNotIn('0xc58600',F)
class Shared(unittest.TestCase):
 def test_18_four_code_one_literal_prior_pin_union(self):
  old=load('t242_prior_all_native_pins');allp=load('t242_all_native_pins');self.assertEqual((len(old),len(allp)),(175,180));self.assertTrue(old.items()<=allp.items())
  for f in [*F.values(),L['exact_constant']]:
   raw=bytes.fromhex(f['raw_hex']);self.assertEqual(len(raw),f['window_size']);self.assertEqual(hashlib.sha256(raw).hexdigest(),f['sha256']);self.assertEqual(allp[f['window_start']+'/'+str(len(raw))]['sha256'],f['sha256'])
 def test_19_current_safe_guards_production_inventory(self):
  for x in [N,T,I,L,G]:self.assertEqual(x['before'],x['after']);self.assertEqual(x['before'],G['before'])
  b=G['before'];self.assertEqual((b['pause'],b['speed_slot'],b['hour_tick']),(1,0,60781105));self.assertFalse(any(b['markers'].values()));self.assertEqual(G['production_baseline_fields'],51);self.assertEqual(len(G['production_hashes']),4);self.assertEqual(hashlib.sha256(Path('/workspace/hoi4-docs-latest/态势信息读取能力清单.md').read_bytes()).hexdigest(),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
 def test_20_offline_setup_failures_not_test_or_live_controls(self):
  z=load('t242_offline_setup_attempts');self.assertEqual((z['offline_switch_generation_starts'],z['completed_generations']),(2,1));self.assertEqual(z['package_setup_attempts'],2);self.assertFalse(z['game_access']);self.assertTrue(z['not_test_collection_failure'])
  for x in [N,T,I,L]:self.assertEqual(x['promotions'],[])
  for p in T['directional_pairs']:self.assertTrue(p['projection_not_raw_schema_field'])
if __name__=='__main__':
 loader=unittest.TestLoader();suite=unittest.TestSuite([loader.loadTestsFromTestCase(Targeted),loader.loadTestsFromTestCase(Shared)]);ids=[t.id() for sub in suite for t in sub];out=io.StringIO();r=unittest.TextTestRunner(stream=out,verbosity=2).run(suite);report=dict(successful=r.wasSuccessful(),unique_methods=len(set(ids)),total_test_invocations=r.testsRun,targeted_methods=17,shared_methods=3,suite_starts=1,completed_suite_runs=1,failures=len(r.failures),errors=len(r.errors),collection_failures=0,method_ids=ids,output=out.getvalue());(Q/'t242_regression_attempt1.json').write_text(json.dumps(report,indent=2)+'\n');print(out.getvalue());raise SystemExit(not r.wasSuccessful())
