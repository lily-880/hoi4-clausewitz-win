# Offline evidence regression only; synthetic boundaries are not live samples.
import unittest,json,hashlib,struct
from pathlib import Path
Q=Path(__file__).resolve().parent
load=lambda n:json.loads((Q/(n+'.json')).read_text(encoding='utf-8'))
B=load('t236_frontage_evaluator_bind');D=load('t236_frontage_dispatch_semantics');T=load('t236_frontage_predicate_tail');R=load('t236_capacity_subject_roots');C=load('t236_raw_capacity_controls_and_plan_pivot')
def asm(d,k):return '\n'.join(d['functions'][k]['asm'])
class Evidence(unittest.TestCase):
 def test_01_factory_rtti_and_subobject(self):
  self.assertEqual(B['vtable_rva'],'0x2832d50');self.assertEqual(B['class_name'],'.?AVCFrontageFullTrigger@@');self.assertEqual(B['col_offset'],0)
 def test_02_supported_scope_not_evaluator(self):
  self.assertIn('mov eax, 0x10',asm(D,'0x494de0'));self.assertEqual(B['slots'][14]['rva'],'0x494de0');self.assertNotEqual(B['slots'][14]['rva'],T['tail_slots'][6]['rva'])
 def test_03_parser_expected_boolean_not_predicate(self):
  self.assertIn('0x592130',asm(B,'0x143e4c0'));self.assertIn('+ 0x58]',asm(D,'0x592130'));self.assertNotIn('0x133e540',asm(D,'0x592130'))
 def test_04_virtual_boolean_dispatch(self):
  self.assertIn('call qword ptr [rax + 0xb0]',asm(B,'0x594370'));self.assertEqual(T['tail_slots'][6]['index']*8,0xb0);self.assertEqual(T['tail_slots'][6]['rva'],'0x492740')
 def test_05_exact_tooltip_names(self):
  names={x['text'] for x in T['functions']['0x4950d0']['literals']};self.assertEqual(names,{'TRIGGER_IS_NOT_FRONTAGE_FULL','TRIGGER_IS_FRONTAGE_FULL'})
 def test_06_subject_null_and_inversion_instructions(self):
  a=asm(T,'0x492740')
  for x in ['[rdx + 0x60]','call 0x133e540','cmp byte ptr [rbx + 0x58], al','setne al','xor al, al']:self.assertIn(x,a)
 def test_07_capacity_minus_effective_sum_strict_positive(self):
  a=asm(R,'0x133e540_full')
  for x in ['[rsi + 0xf4]','[rsi + 0xe8]','[r8 + 0xd0]','[rax + 0x170]','sub rax, rbx','setg al']:self.assertIn(x,a)
  self.assertEqual(R['functions']['0x133e540_full']['unresolved_edges'],[])
 def test_08_synthetic_strict_boundary(self):
  helper=lambda c,ws:c-sum(ws)>0
  self.assertEqual([helper(10,[9]),helper(10,[10]),helper(10,[11])],[True,False,False])
 def test_09_synthetic_expected_boolean_truth_table_and_null(self):
  evaluate=lambda subject,expected,remaining:False if subject is None else expected!=(remaining>0)
  self.assertEqual([evaluate(True,e,r) for e in (False,True) for r in (-1,0,1)],[False,False,True,True,True,False]);self.assertFalse(evaluate(None,True,-1))
 def test_10_current_membership_and_class_controls(self):
  self.assertEqual({x['combat_id'] for x in R['subjects']},{3072,3096,3097});self.assertEqual(sum(len(c['sides']) for c in R['subjects']),6)
  self.assertEqual(sum(s['active_count'] for c in R['subjects'] for s in c['sides']),9)
  for c in R['subjects']:
   self.assertEqual(c['class_name'],'CLandCombat');self.assertEqual(c['width_getter'],'0x133dc00');self.assertTrue(any(u['owner_index']==3 for s in c['sides'] for u in s['active_members']))
   for s in c['sides']:
    self.assertEqual(s['class_name'],'CLandCombatant');self.assertEqual(s['active_count'],len(s['active_members']));self.assertTrue(all(u['width_getter']=='0xcda6a0' for u in s['active_members']))
 def test_11_raw_template_controls_arithmetic(self):
  self.assertEqual(len(C['controls']),6)
  for s in C['controls']:
   self.assertEqual(s['active_count'],len(s['units']));self.assertEqual(s['base_width_sum_raw'],sum(u['base_width_raw'] for u in s['units']))
   for u in s['units']:self.assertEqual(u['base_width_raw'],sum(x['count']*x['width_raw'] for x in u['template_parts']))
  self.assertEqual(sorted(s['base_width_sum_raw'] for s in C['controls']),[800000,800000,1800000,1800000,1800000,6900000])
 def test_12_raw_not_effective_modifiers_required(self):
  a=asm(R,'0xcda6a0');self.assertIn('0x10f',a)
  names={x['text'] for x in R['functions']['0xcda6a0']['literals']};self.assertIn('COMBAT_WIDTH_DIFF',names)
  for s in C['controls']:self.assertTrue(s['effective_width_sum_unproved']);self.assertTrue(s['native_boolean_unproved'])
 def test_13_capacity_terrain_and_direction_not_manpower(self):
  a=asm(R,'0x133dc00')
  for x in ['[rbx + 0xa0]','[rdi + 0x68]','[rdi + 0x70]','call 0x133dcb0']:self.assertIn(x,a)
 def test_14_metadata_stop_and_partial_flow_retained(self):
  self.assertEqual(T['tail_slots'][-1]['index'],23);self.assertFalse(T['tail_slots'][-1]['in_text']);self.assertNotIn(T['tail_slots'][-1]['rva'],T['functions'])
  self.assertTrue(B['functions']['0x596450']['unresolved_edges']);self.assertTrue(T['functions']['0x591f70']['unresolved_edges'])
 def test_15_native_raw_hashes_and_window_identity(self):
  pins=load('t236_available_native_pins');self.assertEqual(len(pins),26)
  for d in (B,D,T,R):
   for label,f in d['functions'].items():
    raw=bytes.fromhex(f['raw_hex']);self.assertEqual(len(raw),f['window_size']);self.assertEqual(hashlib.sha256(raw).hexdigest(),f['sha256']);self.assertIn(f'{f["window_start"]}/{len(raw)}',pins)
 def test_16_fresh_guard_inventory_no_promotion(self):
  for d in (B,D,T,R,C):
   self.assertEqual(d['before'],d['after']);g=d['before'];self.assertEqual((g['pid'],g['base'],g['pause'],g['speed_slot'],g['hour_tick']),(31576,'0x7ff72fc80000',1,0,60781105));self.assertFalse(any(g['markers'].values()));self.assertEqual(d['promotions'],[])
  self.assertEqual(hashlib.sha256((Q/'t236_inventory_before.md').read_bytes()).hexdigest(),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
 def test_17_failed_signed64_read_corrected_not_hidden(self):
  # Native sign-extends only low32. Unrelated high32 can invalidate a signed64 bound.
  data=struct.pack('<QII',0x12345678,9,0x7fffffff);self.assertEqual(struct.unpack_from('<i',data,8)[0],9);self.assertGreater(struct.unpack_from('<q',data,8)[0],100)
  old=(Q/'t236_raw_inputs_attempt1_failed_source.py').read_text();new=(Q/'t236_raw_capacity_controls_and_plan_pivot.py').read_text();self.assertIn("struct.unpack('<Qq'",old);self.assertIn("struct.unpack_from('<i',entry,8)",new)
