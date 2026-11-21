import unittest,json,copy
from pathlib import Path
from t235_frozen_checks import *
Q=Path(__file__).parent
load=lambda n:json.loads((Q/(n+'.json')).read_text())
A=load('t235_named_intel_entrances');B=load('t235_template_count_domain');C=load('t235_named_current_intel_consumer');D=load('t235_country_intel_and_front_full')
class Domains(unittest.TestCase):
 def test_literal_confidence_absence_is_scoped_to_ascii_discovery(self):
  self.assertEqual(A['hits']['confidence'],[]);self.assertEqual(A['total_eligible']['confidence'],0);self.assertIn('not semantics',A['scope'])
 def test_unit_intel_budget_not_saturated(self):
  self.assertEqual(A['total_eligible']['unit_intel'],22);self.assertEqual(len(A['hits']['unit_intel']),22);self.assertEqual(A['per_category_cap'],24)
 def test_army_intel_cap_is_transparent_and_refinement_collected(self):
  self.assertEqual(A['total_eligible']['army_intel'],151);self.assertEqual(len(A['hits']['army_intel']),24);self.assertEqual(len(B['army_intel_names']),86)
 def test_three_name_getters_not_value_getters(self):
  for k,label in [('0x78a470','MAX'),('0x78a480','MIN'),('0x78a490','RANGE_AT_LOWEST_INTEL')]:
   f=B['functions'][k];self.assertEqual(f['reachable_instruction_count'],2);self.assertTrue(f['asm'][0].split()[1]=='lea');self.assertTrue(f['asm'][1].endswith('ret '));self.assertIn('NIntel::ARMY_TEMPLATE_UNIT_COUNT_INTEL_'+label,[x['text'] for x in f['literals']])
 def test_named_army_intel_expression_explicit_country_domain(self):
  self.assertEqual(C['targets']['0x2a47410'],'army intel against a target country. example GER.army_intel@ENG');self.assertIn('0x158aa65',C['refs']['0x2a47410'])
 def test_current_army_intel_amount_is_exactly_named(self):
  f=C['functions']['0x1f2afd0'];self.assertIn({'site':'0x1f2b199','rva':'0x2b047a8','text':'CURRENT_ARMY_INTEL'},f['literals']);self.assertIn('AMOUNT',[x['text'] for x in f['literals']])
 def test_current_army_intel_passes_kind_one_and_country_tags(self):
  a=C['functions']['0x1f2afd0']['asm'];self.assertIn('1f2b0f8 add rcx, 0x1750',a);self.assertIn('1f2b12e mov r9d, 1',a);self.assertIn('1f2b142 call 0x14cb760',a);self.assertIn('1f2b0e5 cmp dword ptr [rax + 0x520], edi',a)
 def test_country_helper_kind_one_selects_second_qword(self):
  a=D['functions']['0x14cb760']['asm'];self.assertIn('14cb7e1 sub edx, 1',a);self.assertIn('14cb7e4 je 0x14cb800',a);self.assertIn('14cb800 mov rax, qword ptr [rax + 8]',a);self.assertIn('14cb7d6 call 0xd65d80',a)
 def test_hundred_percent_shortcut_is_not_live_unit_confidence(self):
  a=D['functions']['0x14cb760']['asm'];self.assertIn('14cb7af mov qword ptr [rbx], 0x186a0',a);self.assertIsNone(confidence_from_research({'branch_raw':100000}))
 def test_named_fuzzy_template_range_is_separate(self):
  texts=[x['text'] for x in C['functions']['0x1f2afd0']['literals']];self.assertIn('FUZZY_INTEL_RANGE_TOOLTIP',texts);self.assertIn('MIN_INTEL_REQUIRED_FOR_BASIC_TEMPLATE_INFO_TOOLTIP',texts);self.assertIn('TEMPLATE_ARMY_COUNT_TITLE',texts)
 def test_exact_frontage_full_token_not_manpower_hold(self):
  self.assertEqual(D['front_full_token'],{'id':13199,'name':'frontage_full'});self.assertIsNone(front_hold_failure_from_frontage({'frontage_full':True}))
 def test_frontage_registration_not_front_hold_proof(self):
  f=C['functions']['0x29fc0'];self.assertIn('check if sides front is full or can get more reinforcements',[x['text'] for x in f['literals']]);self.assertIn('2a00e mov edx, 0x338f',f['asm'])
 def test_descriptor_adjacent_data_not_four_methods(self):
  s=D['descriptor_slots'];self.assertEqual(s[2]['rva'],'0x2c86530');self.assertIsNone(s[2]['pdata']);self.assertEqual(s[0]['rva'],s[3]['rva'])
 def test_factory_initializes_descriptor_not_game_evaluation(self):
  a=D['functions']['0x493900']['asm'];self.assertIn('493906 mov ecx, 0x60',a);self.assertIn('493925 mov byte ptr [rbx + 0x58], 0',a)
 def test_all_native_windows_integrity(self):
  for j in (B,C,D):self.assertTrue(code_integrity(j))
  pins=load('t235_native_pins');self.assertEqual(len(pins),13)
 def test_session_rebinding_and_mutated_guard(self):
  base=A['before']
  for j in (A,B,C,D):self.assertTrue(guard_ok(j['after'],base))
  for key,v in [('pid',10288),('pause',0),('speed_slot',1),('hour_tick',60781106)]:
   g=copy.deepcopy(base);g[key]=v;self.assertFalse(guard_ok(g,base))
 def test_no_country_intel_or_template_define_substitution(self):
  for j in (A,B,C,D,{'country_intel':100000},{'tier':250},{'opacity':255},{'fuzzy_range':10}):self.assertIsNone(confidence_from_research(j))
if __name__=='__main__':unittest.main()
