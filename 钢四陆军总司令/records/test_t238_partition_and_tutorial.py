# Box-only offline evidence tests. LUT/model cases are not native invocations/live positives.
from pathlib import Path
import unittest,json,hashlib,struct
from t238_resolve_static_id_partition import classify,TARGETS,LUT,RAW,BASE
Q=Path(__file__).resolve().parent;L=lambda n:json.loads((Q/(n+'.json')).read_text(encoding='utf-8'));H=lambda b:hashlib.sha256(b).hexdigest()
G=L('t238_fresh_guard');I=L('t238_alert_visibility_filter');D=L('t238_plan_axis_named_entrances');F=L('t238_frontline_named_consumer');T=L('t238_tutorial_plan_predicate_tables');E=L('t238_tutorial_predicate_tail');C=L('t238_tutorial_predicate_continuations');P=L('t238_static_id_partition_proof')
OLD=json.loads(Path('/workspace/hoi4-t237/research/t237_plan_alert_subject_and_cached_control.json').read_text());asm=lambda d,k:'\n'.join(d['functions'][k]['asm'])
class Certificate(unittest.TestCase):
 def test_01_id_only_native_prefix_and_unsigned_gate(self):
  self.assertEqual(RAW[:8],bytes.fromhex('83c2f883fa497721'));a=asm(I,'0xb620c0');self.assertIn('add edx, -8',a);self.assertIn('cmp edx, 0x49',a);self.assertIn('ja 0xb620e9',a)
 def test_02_complete_raw_indirect_case_set(self):
  self.assertEqual(TARGETS,(0xb620e6,0xb620e9));self.assertEqual(len(LUT),74);self.assertEqual(set(LUT),{0,1});self.assertEqual(RAW[0x26:0x29],b'\xb0\x01\xc3');self.assertEqual(RAW[0x29:0x2c],b'\x32\xc0\xc3');self.assertEqual(len(I['functions']['0xb620c0']['unresolved_edges']),1)
 def test_03_passed_receiver_is_not_consumed(self):
  a=asm(I,'0xb620c0');self.assertNotIn('[rcx',a);self.assertIn('mov ecx, dword ptr [rdx + rax*4 + 0xb620ec]',a);self.assertFalse(P['receiver_consumed']);self.assertEqual(P['heap_reads'],0)
 def test_04_lookup_positive_contrasts_not_severity(self):
  self.assertTrue(classify(8));self.assertTrue(classify(81));self.assertEqual(sum(classify(i) for i in range(82)),70);self.assertEqual(P['native_invocations'],0)
 def test_05_qualified_crisis_ids_false_not_severity_ranks(self):
  self.assertEqual(P['false_ids_in_0_81'],[0,1,2,3,4,5,6,7,19,43,45,46]);self.assertFalse(classify(3));self.assertFalse(classify(4));self.assertFalse(classify(43));self.assertEqual(P['genuine_schema_severity_positive_samples'],0);self.assertEqual(P['genuine_schema_severity_negative_samples'],0)
 def test_06_unsigned_wrap_boundaries_and_input_contract(self):
  self.assertFalse(classify(0));self.assertFalse(classify(7));self.assertFalse(classify(82));self.assertFalse(classify(0xffffffff))
  for x in (-1,2**32,True,8.0,'8'):
   with self.assertRaises(ValueError):classify(x)
 def test_07_named_caller_id_loop_not_per_entry_receiver(self):
  a=asm(OLD,'0xb6b9e0')
  for x in ['b6dd90 mov edx, r13d','b6dd93 mov rcx, rsi','b6dd96 call 0xb620c0','b6dd9d je 0xb6df68','b6df76 cmp r13d, 0x52']:self.assertIn(x,a)
  pin=L('t238_prior_all_native_pins')['0xb6b9e0/10516'];self.assertEqual(pin['sha256'],OLD['functions']['0xb6b9e0']['sha256'])
 def test_08_glow_branch_does_not_label_schema_severity(self):
  a=asm(OLD,'0xb6b9e0');self.assertIn('cmp dword ptr [rbx + rdi + 0x430], 2',a);names={x['text'] for x in OLD['functions']['0xb6b9e0']['literals']};self.assertIn('red_alert_glow',names);self.assertIn('yellow_alert_glow',names);self.assertFalse(classify(4))
 def test_09_distinct_discovery_excludes_prior_unit_arrow(self):
  self.assertEqual({x['text'] for x in D['names']},{'frontline','attackArrow'});self.assertEqual(D['functions'],{});self.assertEqual(D['own_plan_registries_read'],0);self.assertEqual(D['references'][0]['site'],'0x1a5c607');self.assertNotIn('0x16e58b0',F['functions'])
 def test_10_frontline_exact_literal_to_constructor(self):
  f=F['functions']['0x1a5bac0'];raw=bytes.fromhex(f['raw_hex']);st=int(f['window_start'],16);ins=raw[0x1a5c669-st:0x1a5c669-st+7];self.assertEqual(ins[:3],b'\x48\x8d\x05');self.assertEqual(0x1a5c670+struct.unpack_from('<i',ins,3)[0],0x2aa0dd8);a=asm(F,'0x1a5bac0');self.assertIn('1a5c5f9 cmp rbx, 9',a);self.assertIn('1a5c607 lea rdx, [rip + 0x1044f8a]',a)
 def test_11_offensive_order_has_separate_named_construction(self):
  a=asm(F,'0x1a5bac0');self.assertIn('1a5c688 cmp rbx, 0xf',a);self.assertIn('1a5c696 lea rdx, [rip + 0x1044f0b]',a);self.assertIn('1a5c6f8 lea rax, [rip + 0x1044739]',a)
 def test_12_rtti_is_tutorial_not_raw_plan(self):
  self.assertEqual([(x['label'],x['class_name'],x['col_offset']) for x in T['tables']],[('frontline','.?AVCTutFrontline@@',0),('offensive_order','.?AVCTutOffensiveOrder@@',0)])
 def test_13_initial_methods_shared_not_guessed_predicate(self):
  self.assertEqual(T['tables'][0]['slots'],T['tables'][1]['slots']);self.assertEqual(T['tables'][0]['slots'][3]['rva'],'0x1a5b7d0');self.assertNotEqual(T['tables'][0]['slots'][3]['rva'],E['tails'][0]['slots'][1]['rva'])
 def test_14_metadata_stop_not_adjacent_table_method(self):
  for t in E['tails']:
   self.assertEqual([x['index'] for x in t['slots']],[8,9,10,11]);self.assertFalse(t['slots'][-1]['in_text']);self.assertNotIn(t['slots'][-1]['rva'],E['functions'])
 def test_15_distinct_slot9_calls_distinct_helpers(self):
  self.assertEqual([x['slots'][1]['rva'] for x in E['tails']],['0x1a61bf0','0x1a61d90']);self.assertIn('call 0x1a57380',asm(C,'0x1a61bf0_full'));self.assertIn('call 0x1a57590',asm(C,'0x1a61d90_full'))
 def test_16_fragment_windows_preserved_and_extended(self):
  for k in ['0x1a61bf0','0x1a61d90']:
   a=E['functions'][k];b=C['functions'][k+'_full'];self.assertEqual(a['window_size'],147);self.assertTrue(a['unresolved_edges']);self.assertEqual(b['window_size'],512);self.assertTrue(b['raw_hex'].startswith(a['raw_hex']));self.assertEqual(b['window_start'],k)
 def test_17_continuation_scope_is_tag_selection_not_axis_vector(self):
  for k in ['0x1a61bf0_full','0x1a61d90_full']:
   f=C['functions'][k];self.assertEqual(f['unresolved_edges'],[]);self.assertEqual(f['external_tails'],[]);a=asm(C,k)
   for x in ['mov edx, 0x520','mov ecx, 0x524','cmovg ecx, edx','add rcx, rax']:self.assertIn(x,a)
  self.assertEqual(C['promotions'],[])
 def test_18_shared_fresh_guard_and_no_mutation_gates(self):
  self.assertTrue(G['safe']);self.assertEqual(G['rechecked_prior_native_windows'],142);self.assertEqual(G['before'],G['after']);self.assertEqual(G['before']['pause'],1);self.assertEqual(G['before']['speed_slot'],0);self.assertFalse(any(G['before']['markers'].values()))
  for d in (I,D,F,T,E,C):self.assertEqual(d['before'],G['before']);self.assertEqual(d['after'],G['before']);self.assertEqual(d['promotions'],[])
 def test_19_shared_raw_pins_start_size_not_label(self):
  cur=L('t238_native_pins');self.assertEqual(len(cur),14);self.assertEqual(len(L('t238_all_native_pins')),154)
  for d in (I,F,T,E,C):
   for label,f in d['functions'].items():
    raw=bytes.fromhex(f['raw_hex']);self.assertEqual(len(raw),f['window_size']);self.assertEqual(H(raw),f['sha256']);self.assertIn(f'{f["window_start"]}/{len(raw)}',cur)
 def test_20_shared_inventory_production_and_no_promotion(self):
  self.assertEqual(G['production_baseline_fields'],51);self.assertEqual(len(G['production_hashes']),4);self.assertEqual(G['version'],'1.19.5.0.7c6c');self.assertEqual(G['country_tag'],'SOV');self.assertEqual(H(Path('/workspace/hoi4-docs-latest/态势信息读取能力清单.md').read_bytes()),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
