import unittest,json,copy
from pathlib import Path
from t234_frozen_checks import *
Q=Path(__file__).parent
A=json.loads((Q/'t234_relation_enqueue_callers.json').read_text())
B=json.loads((Q/'t234_enqueue_completion.json').read_text())
C=json.loads((Q/'t234_pending_list_and_predicates.json').read_text())
class ResearchTests(unittest.TestCase):
 def test_three_wrappers_lea_into_second_endbundle(self):
  t=A['lea_targets']
  self.assertEqual(lea_scope(
   [t[k] for k in t if k.startswith(('f7bb20','f7bce0','f7e1c0'))],
   [t[k] for k in t if k.startswith('f7b940')]), '33eb090')
 def test_notify_controller_changed_path_stays_first_scope(self):
  t=A['lea_targets']
  with self.assertRaises(ValueError):
   lea_scope([t['f7b940_enqueue']],[t['f7e1c0_enqueue']])
 def test_joined_war_literals_are_independently_named(self):
  texts={x['text'] for x in A['functions']['0x118def0']['literals']}
  for n in ('DIPLOMACY_JOINED_WAR_ENEMY','DIPLOMACY_JOINED_WAR_ALLY','DIPLOMACY_JOINED_WAR_TITLE','pWarRelation && "Missing War Relation"','WAR'):
   self.assertIn(n,texts)
 def test_joined_war_calls_f7e1c0_with_null_ecx(self):
  self.assertTrue(null_ecx_before_call(A['functions']['0x118def0']['asm'],'0x118ee12'))
 def test_joined_war_requires_type_field_equals_two(self):
  a=A['functions']['0x118def0']['asm']
  self.assertIn('118df29 cmp dword ptr [rcx + 0x68], 2',a)
  self.assertIn('118df2d jne 0x118ee92',a)
 def test_revoke_guarantee_and_peace_also_null_ecx(self):
  self.assertTrue(null_ecx_before_call(A['functions']['0x118b810']['asm'],'0x118ba6e'))
  self.assertTrue(null_ecx_before_call(A['functions']['0xeb10a0']['asm'],'0xeb1b68'))
  texts={x['text'] for x in A['functions']['0x118b810']['literals']}
  self.assertIn('REVOKE_GUARANTEE_ACTION_THREAT',texts)
  peace={x['text'] for x in A['functions']['0xeb10a0']['literals']}
  self.assertIn('pWarRelation && "A winner and loser within a peace conference do not have a war relation."',peace)
 def test_volunteers_and_theater_removal_share_same_scope_via_other_wrappers(self):
  dest={x['site']:x['dest'] for x in A['callers']}
  self.assertEqual(dest['0x15bc8a9'],'0xf7bce0')
  self.assertEqual(dest['0x74d279'],'0xf7bb20')
  v={x['text'] for x in A['functions']['0x15bc200']['literals']}
  self.assertIn('VOLUNTEER_MESSAGE_ARRIVED',v)
  th={x['text'] for x in A['functions']['0x74d0d0']['literals']}
  self.assertIn('Removing Theater %s from %s',th)
 def test_d56b10_copies_global_pending_list(self):
  a=B['functions']['0xd56b10_tail']['asm']
  self.assertIn('d56b41 mov dword ptr [rcx + 0xc], 0',a)
  self.assertIn('d56bbf mov dword ptr [rsi + 0xc], ebp',a)
  self.assertIn('d56bcf call 0x26079d0',a)
  self.assertEqual(C['pending']['list_object_rva'],'0x33ea908')
  self.assertEqual(C['pending']['count_rva'],'0x33ea914')
 def test_current_pending_list_empty_is_not_schema_false(self):
  p=C['pending']
  self.assertEqual(p['count'],0)
  self.assertFalse(p['player_listed'])
  self.assertFalse(pending_is_schema_value(p))
 def test_predicate_helpers_have_no_independent_names(self):
  for k in ('0x748490','0xda37f0','0x1bd5a0'):
   self.assertEqual(C['functions'][k]['literals'],[])
 def test_f6f9b0_tail_inserts_related_countries_without_named_predicate(self):
  calls=[c['operand'] for c in B['functions']['0xf6f9b0_tail']['calls']]
  for op in ('0x1bd5a0','0x12e040','0x748490','0xda37f0'):
   self.assertIn(op,calls)
 def test_navy_intel_defines_are_not_unit_confidence(self):
  texts=[h['text'] for h in B['intel_literal_hits']]
  self.assertTrue(any('TRIGGER_INTEL_LEVEL_OVER'==t for t in texts))
  for t in texts:
   self.assertIs(navy_intel_define_is_unit_confidence(t),False)
 def test_all_unique_native_windows_integrity(self):
  seen={}
  for j,n in ((A,34-6),(B,'x'),(C,'y')):
   self.assertTrue(code_integrity(j))
  for j in (A,B,C):
   for k,f in j['functions'].items():
    key=(k,f['window_size'])
    if key in seen:self.assertEqual(seen[key],f['sha256'])
    seen[key]=f['sha256']
  pins=json.loads((Q/'t234_native_pins.json').read_text())
  self.assertEqual(len(pins),34)
 def test_current_session_and_mutated_guard(self):
  baseline=A['before']
  for j in (A,B,C):self.assertTrue(strict_guard(j['after'],baseline))
  for key,value in (('pid',10288),('speed_slot',1),('pause',0),('hour_tick',60781106)):
   g=copy.deepcopy(baseline);g[key]=value;self.assertFalse(strict_guard(g,baseline))
 def test_research_does_not_yield_schema_value(self):
  for j in (A,B,C,{'joined_war':True},{'pending_count':0},{'invalid_key':True}):
   self.assertIsNone(schema_front_invalidated_from_research(j))
 def test_twenty_direct_callers_are_exactly_accounted(self):
  self.assertEqual(len(A['callers']),20)
  self.assertEqual({x['dest'] for x in A['callers'] if x['dest']=='0xf7e1c0'}|set(),{'0xf7e1c0'} if any(x['dest']=='0xf7e1c0' for x in A['callers']) else set())
  self.assertEqual(sum(x['dest']=='0xf7e1c0' for x in A['callers']),18)
  self.assertEqual(sum(x['dest']=='0xf7bce0' for x in A['callers']),1)
  self.assertEqual(sum(x['dest']=='0xf7bb20' for x in A['callers']),1)
 def test_intel_search_budget_was_saturated_by_navy_defines(self):
  self.assertEqual(len(B['intel_literal_hits']),40)
  self.assertTrue(all(h['needle']=='INTEL_LEVEL' for h in B['intel_literal_hits']))
if __name__=='__main__':unittest.main()
