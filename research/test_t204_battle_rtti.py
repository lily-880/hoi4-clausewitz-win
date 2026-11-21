import unittest
from input_loaded_fields import LoadedReader
from input_observation import ObservationError
from research._t203_battle_reader import battle_people_loss_candidate
from research.test_t203_delivery_manpower import Memory
class RealReaderRTTI(unittest.TestCase):
 def fixture(self,ns='.?AVCStatsObserver@NCombatLog@@'):
  m=Memory();m.put(0x200000,'<Q',0x300000);m.put(0x2001d0,'<Q',0x400000);m.put(0x200230,'<i',0);names={0x200000:'.?AVCLandCombatant@@',0x2001d0:ns};return m,LoadedReader(m.exact,lambda a:names[a])
 def test_real_loaded_reader_exact_namespace(self):
  m,r=self.fixture();d=battle_people_loss_candidate(r,0x200000);self.assertEqual(d['candidate_people_loss'],0);self.assertFalse(d['schema_emission']);self.assertGreaterEqual(r.stable(),3)
 def test_wrong_namespace_still_rejected(self):
  m,r=self.fixture('.?AVCStatsObserver@@')
  with self.assertRaises(ObservationError):battle_people_loss_candidate(r,0x200000)
 def test_vptr_stability_tracked(self):
  m,r=self.fixture();battle_people_loss_candidate(r,0x200000);m.put(0x2001d0,'<Q',0x500000)
  with self.assertRaises(ObservationError):r.stable()

class RouteMapIndirection(unittest.TestCase):
 def test_pointer_not_inline(self):
  from research.test_t203_delivery_manpower import fixture
  from research._t203_delivery_reader import delivery_possible
  m,g,a,*_=fixture();self.assertEqual(m.q(0x1600080),0x1b00000);v,e=delivery_possible(m,g,a);self.assertTrue(v);self.assertEqual(e['branch'],'reachable_port')
 def test_null_route_map_not_empty_false(self):
  from research.test_t203_delivery_manpower import fixture
  from research._t203_delivery_reader import delivery_possible
  m,g,a,*_=fixture();m.put(0x1600080,'<Q',0)
  with self.assertRaises(ObservationError):delivery_possible(m,g,a)

class NewNativeEvidence(unittest.TestCase):
 def get(self,n):
  import json
  from pathlib import Path
  return json.loads((Path(__file__).resolve().parent/n).read_text(encoding='utf8'))
 def test_official_manpower_lost_token(self):
  d=self.get('t204_ui_supply_owner_bindings.json')['token_registration'];self.assertEqual(d['value'],0x3750);self.assertEqual(d['name'],'manpower_lost')
 def test_actual_side_data_struct(self):
  d=self.get('t204_stats_member_vtable.json');self.assertEqual(d['class'],'.?AUSCombatSideData@CStatsObserver@NCombatLog@@')
 def test_real_current_area_port_map(self):
  d=self.get('t204_existing_port_map_audit.json');self.assertEqual(d['errors'],[]);self.assertFalse(d['schema_emission']);p=[p for r in d['pairs']for p in r['ports']];self.assertEqual(p[0]['province_id'],12766);self.assertGreaterEqual(p[0]['route'],0)
 def test_supply_is_secondary_base_not_standalone_rtti(self):
  d=self.get('t204_ui_supply_owner_bindings.json')['supply'];self.assertEqual(d['complete_class'],'.?AVCArmy@@');self.assertEqual(d['subobject_offset'],0x10);self.assertIn('.?AVCSupplyConsumer@@',d['base_hierarchy'])
 def test_ui_orientation_not_fixed_first_side(self):
  d=self.get('t204_flag_ui_follow_functions.json')['0x178f070']['asm'];s='\n'.join(d);self.assertIn('178f7a6 cmp byte ptr [rax + 0x447], 0',s);self.assertIn('178f79e mov r9d, r15d',s);self.assertIn('178f7a1 mov esi, 0x220',s);self.assertIn('178f7ad cmove r9d, esi',s)
 def test_birth_zero_and_finalize_copy(self):
  from pathlib import Path
  root=Path(__file__).resolve().parent;a=(root/'_t204_clip_d38460.txt').read_text();self.assertIn('d38479 mov dword ptr [rcx + 8], eax',a);a=(root/'_t204_clip_d3b6d0.txt').read_text();self.assertIn('d3b7ec or byte ptr [rdi], 4',a);self.assertIn('d3b9b7 call 0xd38c90',a)

class ArtifactUTF8(unittest.TestCase):
 def test_seal_never_uses_windows_default_codec(self):
  import ast
  from pathlib import Path
  t=ast.parse((Path(__file__).resolve().parent/'_t204_seal.py').read_text(encoding='utf8'));calls=[n for n in ast.walk(t)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='read_text'];self.assertGreater(len(calls),0);self.assertTrue(all(any(k.arg=='encoding'for k in n.keywords)for n in calls))
