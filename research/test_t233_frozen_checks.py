import unittest,json,copy
from pathlib import Path
from t233_frozen_checks import *
Q=Path(__file__).parent
load=lambda n:json.loads((Q/(n+'.json')).read_text())
V=load('t233_validator_probe');B=load('t233_front_builder_chain');P=load('t233_rebuild_scope_and_predicate');E=load('t233_named_bundle_enqueue')
T=P['own_theatres'][0]
class ResearchTests(unittest.TestCase):
 def test_direct_key_valid_without_enemy(self):self.assertEqual(resolve_key(123),123)
 def test_null_both_keys_rejected(self):self.assertIsNone(resolve_key(0))
 def test_empty_enemy_controller_list_rejected(self):self.assertIsNone(resolve_key(0,0,123))
 def test_null_first_controller_rejected(self):self.assertIsNone(resolve_key(0,3,0))
 def test_enemy_first_controller_valid(self):self.assertEqual(resolve_key(0,3,123),123)
 def test_all_five_actual_predicates_valid(self):
  self.assertEqual(len(T['dictionary_rows']),5)
  for x in T['dictionary_rows']:
   a=int(x['area'],16);first=int(x['resolved_controller_area'],16);resolved=resolve_key(a,x.get('enemy_controller_count'),first)
   self.assertEqual(resolved,first);self.assertFalse(x['invalid_entry_predicate']);self.assertEqual(x['resolved_class'],'.?AVCControllerArea@@')
 def test_exact_live_own_front_ids(self):
  own_membership(T);self.assertEqual({x['id'] for x in T['fronts']},{1278,76,70,1734,1735})
 def test_neighbor_theatre_membership_rejected(self):
  t=copy.deepcopy(T);t['fronts'][0]['theatre_back']='foreign'
  with self.assertRaises(ValueError):own_membership(t)
 def test_duplicate_members_rejected(self):
  t=copy.deepcopy(T);t['fronts'].append(t['fronts'][0])
  with self.assertRaises(ValueError):own_membership(t)
 def test_nonmember_dictionary_front_rejected(self):
  t=copy.deepcopy(T);t['dictionary_rows'][0]['front']='foreign'
  with self.assertRaises(ValueError):own_membership(t)
 def test_enemy_keys_not_polymorphic_controller_areas(self):
  rows=[x for x in T['dictionary_rows'] if int(x['enemies_area'],16)];self.assertEqual(len(rows),2)
  self.assertTrue(all(x['enemies_area_class']=='unproved:AssertionError' for x in rows))
 def test_first_controller_is_not_retained_area_identity(self):
  self.assertEqual(sum(not x['matches_front_area'] for x in T['dictionary_rows']),2)
  self.assertEqual(sum(x['matches_front_area'] for x in T['dictionary_rows']),3)
 def test_exact_named_diagnostic_and_constructor(self):
  f=V['functions']['0xf69f30'];self.assertIn({'site':'0xf6a071','rva':'0x29f2460','text':'Fronts per enemy area dictionary has an invalid entry'},f['literals'])
  a=f['asm'];self.assertIn('f6a0a0 mov ecx, 0x88',a);self.assertIn('f6a0a5 call 0x25a01dc',a);self.assertIn('f6a12c mov qword ptr [r15 + 0x10], rdi',a)
 def test_exact_direct_build_caller(self):
  self.assertEqual(V['callers'],[{'site':'0xf78b77','function':'0xf78600'}]);a=V['functions']['0xf78600']['asm'];self.assertIn('f78b7c add rdi, 0xc0',a)
 def test_front7d_has_province_membership_write(self):
  a=B['functions']['0xf6af50']['asm'];self.assertIn('f6afc2 mov byte ptr [rip + 0x2480048], 1',a);self.assertIn('f6afb5 mov byte ptr [rbx + 0x7d], 1',a);self.assertIn('f6af83 je 0xf6af96',a)
 def test_named_endbundle_is_not_war_event(self):
  f=P['functions']['0xf71ed0'];names=[x['text'] for x in f['literals']];self.assertIn('g_OccupationBundleConquer._IsActive >= 0 && g_OccupationBundleRelation._IsActive >= 0',names);self.assertIn('theatremanager.endbundle',names)
  self.assertEqual(len(E['bundles']),2);self.assertEqual({x['mode_byte'] for x in E['bundles']},{0,1});self.assertTrue(all(x['country_count']==x['active_nesting']==x['locked']==0 for x in E['bundles']))
 def test_independently_named_controller_changed_enqueue(self):
  f=E['functions']['0xef1860'];self.assertIn('Call NotifyControllerChanged with %s, %s',[x['text'] for x in f['literals']]);self.assertIn({'site':'0xef24f7','operand':'0xf7b940'},f['calls'])
 def test_all_nineteen_unique_native_windows_integrity(self):
  fs={}
  for j in [V,B,P,E]:
   self.assertTrue(code_integrity(j))
   for k,f in j['functions'].items():
    if k in fs:self.assertEqual(fs[k],f['sha256'])
    fs[k]=f['sha256']
  self.assertEqual(len(fs),19)
 def test_current_session_and_mutated_guard(self):
  baseline=V['before']
  for j in [V,B,P,E]:self.assertTrue(strict_guard(j['after'],baseline))
  for key,value in [('pid',10288),('speed_slot',1),('pause',0),('hour_tick',60781106)]:
   g=copy.deepcopy(baseline);g[key]=value;self.assertFalse(strict_guard(g,baseline))
 def test_neither_empty_bundle_nor_valid_dictionary_yields_schema_value(self):
  for j in [V,B,P,E,{'byte7d':True},{'invalid_entry_predicate':True}]:self.assertIsNone(schema_invalidated_from_research(j))
if __name__=='__main__':unittest.main()
