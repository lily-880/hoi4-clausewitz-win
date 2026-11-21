# Offline checks of exact native evidence. Synthetic equations are not live controls.
import unittest,json,hashlib,struct
from pathlib import Path
Q=Path(__file__).resolve().parent
L=lambda n:json.loads((Q/(n+'.json')).read_text(encoding='utf-8'))
A=L('t237_named_plan_alert_entrance');B=L('t237_plan_alert_registration_and_inserters');C=L('t237_plan_alert_subject_and_cached_control');G=L('t237_fresh_guard');REC=L('t237_reconcile_receipt')
asm=lambda d,k:'\n'.join(d['functions'][k]['asm'])
H=lambda b:hashlib.sha256(b).hexdigest()
def raw_qualifies(count,special,flag298,owner_a4,nested_counts):
 # Only an offline projection of exactly captured branch equations, not status meanings.
 if special:
  if flag298 and owner_a4!=0:return True
  count=sum(nested_counts)
 return count==0
class PlanAlert(unittest.TestCase):
 def test_01_recovery_26_and_audit_bytes(self):
  self.assertTrue(REC['pending_24_authority_copies_resolved']);self.assertTrue(REC['two_laptop_helper_jsons_retrieved']);self.assertEqual(len(REC['entries']),26)
  root=Path('/workspace/hoi4-docs-latest/records')
  for e in REC['entries']:
   p=root/e['name'];self.assertEqual(p.stat().st_size,e['size']);self.assertEqual(H(p.read_bytes()),e['sha256'])
 def test_02_fresh_safe_guard_and_135_pins(self):
  self.assertTrue(G['safe']);self.assertTrue(G['roots_fresh']);self.assertEqual(G['before'],G['after']);self.assertEqual(G['version'],'1.19.5.0.7c6c');self.assertEqual(G['country_tag'],'SOV');self.assertEqual(G['rechecked_prior_native_windows'],135)
  for d in (A,B,C):self.assertEqual(d['before'],G['before']);self.assertEqual(d['before'],d['after']);self.assertEqual(d['promotions'],[])
 def test_03_exact_literal_reference(self):
  self.assertEqual(A['target'],dict(rva='0x29c3dd0',text='alert_battleplans_with_no_divs'));self.assertEqual(len(A['sites']),1);self.assertEqual(A['sites'][0]['site'],'0xb51dbc')
  f=A['functions']['0xb50ab0'];raw=bytes.fromhex(f['raw_hex']);off=0xb51dbc-int(f['window_start'],16);inst=raw[off:off+7];self.assertEqual(inst[:3],b'\x48\x8d\x15');self.assertEqual(0xb51dbc+7+struct.unpack_from('<i',inst,3)[0],0x29c3dd0)
 def test_04_registration_id43_not_adjacent(self):
  a=asm(A,'0xb50ab0');self.assertIn('b51dd4 mov edx, 0x2b',a);self.assertIn('b51ddc call 0xb61660',a);self.assertIn('b51da5 mov edx, 0x2a',a);self.assertIn('b51e03 mov edx, 0x2c',a)
 def test_05_descriptor_name_stride(self):
  a=asm(B,'0xb61660');self.assertIn('imul rcx, rax, 0x468',a);self.assertIn('add rcx, 0x410',a);self.assertEqual(C['descriptor_name'],A['target']['text'])
 def test_06_candidate_byte_scan_verified_by_instruction_dataflow(self):
  self.assertEqual(len(B['candidate_sites']),1);self.assertEqual(B['candidate_sites'][0]['site'],'0xb6fbdd');a=asm(B,'0xb6f730');self.assertIn('b6fbd5 mov edx, 0x2b',a);self.assertIn('b6fbdd call 0xb54c00',a)
 def test_07_corresponding_removal_aggregate_key(self):
  a=asm(B,'0xb6f730')
  for s in ['b6fbce mov r9, qword ptr [rbp + 0x48]','b6fbd2 xor r8d, r8d','b6fbea mov edx, 0x2b','b6fbf2 call 0xb6a2b0']:self.assertIn(s,a)
 def test_08_updater_own_theatre_group_bridge_not_per_plan_key(self):
  a=asm(C,'0xb6b9e0')
  for s in ['[rdi + 0x168]','call 0xd3cb00','b6bbfd sub edx, 3','b6bc02 sub edx, 1','b6bc07 cmp edx, 0x27','b6bc0c mov rdx, r9','b6bc12 call 0xb6f730']:self.assertIn(s,a)
  self.assertEqual(43-3-1,0x27);self.assertIn('lea rax, [rcx + 0xc8]',asm(C,'0xd3cb00'))
 def test_09_subject_container_and_two_parent_arrays(self):
  self.assertIn('lea rax, [rcx + 0x48]',asm(C,'0xd73190'));a=asm(B,'0xb6f730')
  for s in ['call 0xd73190','[rdi + 0x98]','[rdi + 0xa4]','[rdi + 0xb0]','[rdi + 0xbc]']:self.assertIn(s,a)
 def test_10_exact_count_selector_not_generic_status(self):
  a=asm(C,'0xb5bb40')
  for s in ['[rdx + 0x21c]','[rdi + 0x38]','[rax + 0x39]','[rdi + 0x298]','[rax + 0xa4]','[rax + 0x23c]','[rax + 0x230]','[rax + 0x5c]']:self.assertIn(s,a)
 def test_11_child_recursion_and_deduplication(self):
  a=asm(C,'0xb5bb40')
  for s in ['[rdi + 0x204]','[rdi + 0x1f8]','call 0xb5bb40','cmp qword ptr [rax], rdi','call 0x121d60']:self.assertIn(s,a)
 def test_12_synthetic_selector_contrasts_not_native_samples(self):
  self.assertTrue(raw_qualifies(0,False,False,0,[]));self.assertFalse(raw_qualifies(1,False,False,0,[]))
  self.assertTrue(raw_qualifies(8,True,False,0,[]));self.assertFalse(raw_qualifies(0,True,False,0,[2]))
  self.assertTrue(raw_qualifies(8,True,True,2,[2]));self.assertFalse(raw_qualifies(0,True,True,0,[2]))
 def test_13_cached_absence_not_fresh_predicate_or_plan_control(self):
  self.assertEqual(C['alert43'],dict(pointer='0x0',capacity=0,count=0,inspected=0,rows=[]));self.assertEqual(C['own_plan_registries_read'],0);self.assertEqual(C['plan_instances_inspected'],0)
 def test_14_raw_sha_and_window_boundaries(self):
  for d in (A,B,C):
   for f in d['functions'].values():
    raw=bytes.fromhex(f['raw_hex']);self.assertEqual(len(raw),f['window_size']);self.assertEqual(H(raw),f['sha256'])
 def test_15_partial_scheduling_cfg_not_whole_function(self):
  self.assertEqual(len(C['functions']['0xb6b9e0']['unresolved_edges']),2)
  for f in (A['functions']['0xb50ab0'],B['functions']['0xb61660'],B['functions']['0xb6f730'],C['functions']['0xb5bb40']):self.assertEqual(f['unresolved_edges'],[])
 def test_16_native_windows_and_inventory_preserved(self):
  self.assertEqual(len(L('t237_native_pins')),7);self.assertEqual(len(L('t237_all_native_pins')),142);self.assertEqual(G['production_baseline_fields'],51);self.assertEqual(len(G['production_hashes']),4)
  self.assertEqual(H(Path('/workspace/hoi4-docs-latest/态势信息读取能力清单.md').read_bytes()),'8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3')
 def test_17_failed_rtti_assumption_removed_not_asserted_class(self):
  old=(Q/'t237_cached_control_attempt1_failed_source.py').read_text();new=(Q/'t237_plan_alert_subject_and_cached_control.py').read_text();self.assertIn('manager_class=rt.cls(manager)',old);self.assertIn('manager_class=None',new);self.assertIsNone(C['manager_class'])
