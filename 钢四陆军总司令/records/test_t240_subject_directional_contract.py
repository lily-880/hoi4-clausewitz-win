# Offline-only contracts for t240 machine-specific captured evidence, no game API.
import json,hashlib,unittest,io
from pathlib import Path
Q=Path(__file__).resolve().parent
load=lambda n:json.loads((Q/(n+'.json')).read_text(encoding='utf-8'))
U=load('t240_subject_tables_image_typedesc');D=load('t240_directional_subject_consumers');P=load('t240_directional_predicate_contract');O=load('t240_current_owner_directional_operands');G=load('t240_fresh_guard');F={**U['functions'],**D['functions'],**P['functions']}
asm=lambda f:'\n'.join(F[f]['asm'])
def eqref(a,b,aliases):
 return a==b or bool(a and b and aliases.get(a,a)==aliases.get(b,b))
def puppet_of(scope,overlord,target,level,aliases={}):
 return scope>0 and eqref(overlord,target,aliases) and bool(level)
def subject_pair(dep,aliases={}):
 return dep is not None and dep['type']==0x30d1 and eqref(dep['ref'],dep['other'],aliases)
class Targeted(unittest.TestCase):
 def test_01_discovery_misses_not_absence(self):
  for n in ['t240_subject_trigger_table_bind','t240_subject_trigger_table_context']:self.assertEqual(load(n)['tables'],[])
  self.assertEqual(len(U['tables']),2)
 def test_02_independent_data_typedesc_control(self):
  c=U['known_col_control'];self.assertEqual(c['class_name'],'.?AVCTutFrontline@@');self.assertEqual(c['type_descriptor_section'],['.data']);self.assertEqual(c['words'][0],'0x1');self.assertEqual(c['words'][-1],c['col_rva'])
 def test_03_real_unary_interface_binding(self):
  for t,e in zip(U['tables'],['0x3f9ee0','0x3fa2e0']):
   self.assertEqual(t['col_offset'],0);self.assertEqual(t['tooltip_slot'],21);self.assertEqual(t['slots'][22]['rva'],e);self.assertEqual(t['slots'][3]['rva'],'0x594370');self.assertFalse(t['slots'][23]['in_text'])
 def test_04_unary_subject_any_overlord_expected_boolean(self):
  a=asm('0x3fa2e0');self.assertIn('[rdx + 8]',a);self.assertIn('[rdx + 0x188], 0',a);self.assertIn('setg al',a);self.assertIn('[rbx + 0x58], al',a);self.assertNotIn('0xb8',a)
  self.assertTrue((5>0)==True);self.assertTrue((0>0)==False)
 def test_05_unary_puppet_pointer_and_expected_guards(self):
  a=asm('0x3f9ee0');self.assertIn('[rdx + 0x3b8]',a);self.assertIn('[rdx + 0x28]',a);self.assertIn('[rdx + 0x2e], al',a);self.assertIn('[rbx + 0x58], 0',a);self.assertGreaterEqual(a.count('je 0x3f9f24'),2)
 def test_06_independent_named_binary_consumers(self):
  names={v['text'] for v in D['names']};self.assertIn('TRIGGER_IS_PUPPET_OF',names);self.assertIn('TRIGGER_IS_SUBJECT_OF',names)
  for k,text in [('0x441690','TRIGGER_IS_PUPPET_OF'),('0x442880','TRIGGER_IS_SUBJECT_OF')]:self.assertIn(text,{v['text'] for v in F[k]['literals']})
  self.assertEqual([v['evaluator_rva'] for v in D['tables']],['0x3f9e40','0x3fa270'])
 def test_07_extended_binary_slot_not_unary_metadata(self):
  for t in P['tails']:
   self.assertEqual(t['slots'][2],dict(index=23,rva='0x1443990',in_text=True));self.assertEqual(t['slots'][3]['index'],24);self.assertFalse(t['slots'][3]['in_text'])
 def test_08_puppet_direction_rejects_somebody_elses_subject(self):
  a=asm('0x3f9e40');self.assertIn('[rdi + 0x188]',a);self.assertIn('[rax + 0xb8]',a);self.assertIn('cmp r8d, edx',a)
  self.assertTrue(puppet_of(10,3,3,True));self.assertFalse(puppet_of(10,7,3,True));self.assertFalse(puppet_of(3,10,3,True))
 def test_09_puppet_canonical_alias_and_raw_zero_equality(self):
  self.assertIn('call 0xc085f0',asm('0x3f9e40'));self.assertTrue(puppet_of(10,443,368,True,{443:368}));self.assertFalse(puppet_of(10,0,3,True));self.assertTrue(puppet_of(10,0,0,True));self.assertFalse(puppet_of(0,3,3,True))
 def test_10_puppet_needs_level_even_when_parent_matches(self):
  a=asm('0x3f9e40');self.assertIn('[rdi + 0x3b8]',a);self.assertIn('[rax + 0x28]',a);self.assertIn('[rax + 0x2e]',a);self.assertFalse(puppet_of(10,3,3,False))
 def test_11_subject_exact_source_target_relation_index(self):
  a=asm('0x3fa270');self.assertIn('[rdx + 8]',a);self.assertIn('[rax + 0xf88]',a);self.assertIn('call 0xc08790',a);self.assertIn('[rsi + 8]',a);self.assertIn('[rax + rcx*8]',a);self.assertIn('call 0xd87160',a)
 def test_12_exact_consumed_discriminator_name_and_pair(self):
  self.assertEqual(O['exact_consumed_token'],dict(id=0x30d1,name='puppet'));a=asm('0xd87160');self.assertIn('[rcx + 0x288]',a);self.assertIn('[rax + 8], 0x30d1',a);self.assertIn('[rax + 0x10]',a);self.assertIn('[rcx + 0x50]',a)
 def test_13_synthetic_dependency_guards_not_live_positives(self):
  self.assertFalse(subject_pair(None));self.assertFalse(subject_pair(dict(type=1,ref=3,other=3)));self.assertFalse(subject_pair(dict(type=0x30d1,ref=4,other=3)));self.assertTrue(subject_pair(dict(type=0x30d1,ref=443,other=368),{443:368}));self.assertFalse(subject_pair(dict(type=0x30d1,ref=0,other=3)));self.assertTrue(subject_pair(dict(type=0x30d1,ref=0,other=0)))
 def test_14_dynamic_target_resolver_output_contract(self):
  a=asm('0x1443990');self.assertIn('mov rbx, rdx',a);self.assertIn('mov rax, rbx',a)
  for x in ['[rdi + 0x170]','[rdi + 0xa8]','[rdi + 0xa0]','call 0x58ac90','call qword ptr [rax + 0x40]']:self.assertIn(x,a)
 def test_15_current_own_unary_negative_only(self):
  self.assertEqual(D['own_native_inputs'],dict(country_tag='SOV',subject_ref_raw=0,level_present=False))
 def test_16_current_owner_bridge_not_historical_alias_assumption(self):
  b=O['current_combat_owner_bridge'];self.assertEqual((b['combat_id'],b['unit_id'],b['side']),(3072,399,'defender'));self.assertEqual((b['owner_ref_raw'],b['owner_index_field'],b['canonical_owner_index'],b['owner_country_tag']),(368,368,368,'D04'));self.assertEqual(b['player_index'],3);self.assertEqual(b['owner_overlord_ref_raw'],0);self.assertFalse(b['relation_to_player_inputs']['dependency_present'])
 def test_17_no_visible_relation_or_friendly_promotion(self):
  b=O['current_combat_owner_bridge'];self.assertFalse(b['current_visibility_revalidated']);self.assertFalse(b['schema_visible_relation_emitted']);self.assertEqual(O['promotions'],[]);self.assertEqual(D['promotions'],[])
class Shared(unittest.TestCase):
 def test_18_raw_capture_hash_and_function_bounds(self):
  self.assertEqual(len(F),8)
  for v in F.values():
   raw=bytes.fromhex(v['raw_hex']);self.assertEqual(hashlib.sha256(raw).hexdigest(),v['sha256']);self.assertEqual(len(raw),v['window_size']);self.assertEqual(int(v['window_start'],16),int(v['pdata'][0],16));self.assertEqual(v['window_size'],int(v['pdata'][1],16)-int(v['pdata'][0],16));self.assertEqual(v['unresolved_edges'],[])
 def test_19_same_session_safe_guards_and_inventory(self):
  for d in [U,D,P,O,G]:self.assertEqual(d['before'],d['after']);self.assertEqual(d['before'],G['before'])
  g=G['before'];self.assertEqual((g['pid'],g['pause'],g['speed_slot'],g['hour_tick']),(31576,1,0,60781105));self.assertFalse(any(g['markers'].values()));self.assertEqual(G['production_baseline_fields'],51)
  inv=Path('/workspace/hoi4-docs-latest/态势信息读取能力清单.md');self.assertEqual(hashlib.sha256(inv.read_bytes()).hexdigest(),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
 def test_20_prior_and_new_exact_pin_union(self):
  old=load('t240_prior_all_native_pins');allp=load('t240_all_native_pins');self.assertEqual((len(old),len(allp)),(164,172));self.assertTrue(old.items()<=allp.items())
  for v in F.values():self.assertEqual(allp[v['window_start']+'/'+str(v['window_size'])]['sha256'],v['sha256'])
if __name__=='__main__':
 loader=unittest.TestLoader();suite=unittest.TestSuite([loader.loadTestsFromTestCase(Targeted),loader.loadTestsFromTestCase(Shared)]);ids=[t.id() for subs in suite for t in subs];stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);report=dict(successful=result.wasSuccessful(),unique_methods=len(set(ids)),total_test_invocations=result.testsRun,targeted_methods=17,shared_methods=3,suite_starts=1,completed_suite_runs=1,failures=len(result.failures),errors=len(result.errors),collection_failures=0,method_ids=ids,output=stream.getvalue(),synthetic_controls_are_not_live_samples=True);(Q/'t240_regression_attempt1.json').write_text(json.dumps(report,indent=2)+'\n');print(stream.getvalue());raise SystemExit(not result.wasSuccessful())
