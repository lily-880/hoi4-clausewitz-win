import ast,json,sys,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
R=Path(__file__).resolve().parents[1]
def load(n):return json.loads((R/'research'/n).read_text(encoding='utf-8'))
def clip(a):return (R/f'research/_t202_clip_{a:x}.txt').read_text(encoding='utf-8')
class Tests(unittest.TestCase):
 def test_group_pointer_is_not_parent(self):
  d=load('t202_renderer_loss_bridge.json')['plan_group_binding'];self.assertEqual(len(d),6);self.assertEqual({x['rtti']for x in d},{'.?AVCOrdersGroup@@'});self.assertEqual(len({x['orders_group_ptr38']for x in d}),2);self.assertTrue(all('orders_group_id8'not in x for x in d))
 def test_nonempty_real_type_links(self):
  p={x['id']:x for x in load('t202_damage_parent_links.json')['plan_type_links']};self.assertEqual(p[3]['links_1e0'],[{'id':4,'type_raw':1}]);self.assertEqual(p[4]['links_1e0'],[{'id':2,'type_raw':2}]);self.assertIn('[rcx + 0x1e0]',clip(0x10b9ed0));self.assertIn('[rcx + 0x30], edx',clip(0x10b9ed0))
 def test_renderer_abi_not_instance_offset(self):
  d=load('t202_renderer_loss_bridge.json')['renderer_callers'];self.assertEqual(len(d),5);a=clip(0xfcf8f0);self.assertIn('mov qword ptr [rsp + 0x28], r14',a);self.assertIn('lea rbx, [r14 + 0x70]',a);self.assertIn('xor r9d, r9d',a);self.assertIn('mov rsi, qword ptr [rbp + 0x298]',clip(0x12e6e20));self.assertTrue(all(x['midpoints_count']==0 for x in load('t202_deep_semantics.json')['plan_geometry_inputs']))
 def test_tactic_is_not_casualty(self):
  d=load('t202_native_stat_axis.json')['combat_side_stats'];self.assertEqual(len(d),4);self.assertEqual({x['stats_rtti']for x in d},{'.?AVCCombatTactic@@'});self.assertTrue(any(x['raw_fields_138_through160']['0x148']<0 for x in d))
 def test_air_support_record_is_not_manpower(self):
  self.assertEqual(load('t202_native_stat_axis.json')['record_class']['rtti'],'.?AVCAirInLandCombat@@');self.assertIn('lea rcx, [r14 + 0x140]',clip(0x1349780));self.assertTrue(all(not x['array_140']for x in load('t202_deep_semantics.json')['live_combatant_record_candidates']))
 def test_real_damage_is_hp_and_org(self):
  self.assertIn('[rcx + 0x420]',clip(0xce4d70));self.assertIn('[rcx + 0x428]',clip(0xce4d60));a=clip(0xcec2e0);self.assertIn('sub qword ptr [r15 + 0x420], rbx',a);self.assertIn('mov qword ptr [r15 + 0x428], rcx',a);d=load('t202_damage_parent_links.json')['live_damage_counters'];self.assertEqual(len(d),4);self.assertTrue(all(x['field178']>0 and x['field180']>0 for x in d))
 def test_creation_value_is_id_not_date(self):
  a=clip(0x1fa590);self.assertIn('mov dword ptr [rdx], 0x3e',a);self.assertIn('mov eax, dword ptr [rcx + 0x748]',a);self.assertIn('inc eax',a);self.assertIn('mov dword ptr [rdx + 4], eax',a)
 def test_old_full_exports_still_incomplete(self):
  a=load('t201_full_capture_recursive_a.json');b=load('t201_full_capture_recursive_b.json');self.assertEqual(a['observation'],b['observation']);schema=json.loads((R/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'));errors=list(Draft202012Validator(schema).iter_errors(a['observation']));self.assertEqual(len(errors),52);self.assertTrue(all(e.validator=='required'for e in errors));self.assertFalse(a['complete_input']);self.assertTrue(all('casualties'not in x and 'started_at'not in x and 'ended_at'not in x for x in a['observation']['world']['combats']))
 def test_all_research_guards_remain_paused(self):
  names=('t202_deep_semantics.json','t202_renderer_loss_bridge.json','t202_native_stat_axis.json','t202_damage_parent_links.json','t202_template_reason_sources.json','t202_isolated_binding.json','t202_delivery_reason_branch.json','t202_delivery_callers.json','t202_manpower_removal_chain.json');seen=[]
  for n in names:
   d=load(n);g=d['guard_after'];self.assertEqual((g['pid'],g['pause'],g['speed_slot'],g['date']['hour_tick']),(12948,1,0,60759398));self.assertFalse(g['gate_open']);self.assertEqual(len(g['plans']),6);self.assertTrue(all(not x['executing']for x in g['plans']));seen.append(g)
  self.assertTrue(all(g==seen[0]for g in seen))
 def test_new_live_helpers_have_no_mutation_calls(self):
  names=('_t202_common.py','_t202_start.py','_t202_follow.py','_t202_deep.py','_t202_bridge.py','_t202_native.py','_t202_damage.py','_t202_template.py','_t202_isolated.py','_t202_reason.py','_t202_delivery_xrefs.py','_t202_manpower.py')
  for n in names:
   src=(R/'research'/n).read_text(encoding='utf-8');tree=ast.parse(src);calls=[a.func.attr if isinstance(a.func,ast.Attribute)else a.func.id if isinstance(a.func,ast.Name)else ''for a in ast.walk(tree)if isinstance(a,ast.Call)]
   for bad in('do_post','_remote','WriteProcessMemory','factory_make','Execute','execute','capture','exec','write_memory'):self.assertNotIn(bad,calls,n)
   self.assertNotIn('image_path',src);self.assertNotIn('_t198_order_sample',src)
 def test_manpower_is_separate_from_hp_loss(self):
  d=load('t202_manpower_removal_chain.json');self.assertEqual(len(d['frontline_manpower']),14);self.assertTrue(all(x['current']==x['engine_need_total']for x in d['frontline_manpower']));hits=[x for x in d['removal_callers']if x['target']=='0xcc6bf0'];self.assertEqual(len(hits),1);self.assertEqual(hits[0]['site'],'0xc4b0d4');self.assertTrue(all('casualties'not in x for x in d['frontline_manpower']))
 def test_out_of_table_slot_is_rejected(self):
  d=load('t202_isolated_binding.json');self.assertNotIn('primary_changer_predicate',d);self.assertIn('rejected_unbound_slot_candidate',d);self.assertIn('possibly cut off',d['label']);rows=[x for x in load('t202_template_reason_sources.json')['tables']if x['name']=='.?AVCTemplateChanger@@'];self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['slots']),6)
if __name__=='__main__':unittest.main()
