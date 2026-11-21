import json,sys,struct,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'calling'))
from input_loaded_fields import own_plans
from input_observation import ObservationError
from research.test_t198_plan_path_active_combat import Fake
class Tree(Fake):
 def __init__(self):
  super().__init__();self.arr.update({0x41f8:[0x6000],0x61f8:[0x7000]});self.n.update({0x6244:4,0x7244:3})
 def exact(self,a,n):
  if a in(0x6248,0x7248):return b'\0'
  if a in(0x6070,0x7070):return struct.pack('<QII',0,0,0)
  return super().exact(a,n)
class Tests(unittest.TestCase):
 def test_two_levels_are_exported(self):
  p,e=own_plans(Tree(),0x1000);self.assertEqual([x['plan_id']for x in p],[2,6,4,3]);self.assertEqual((e['root_instance_count'],e['recursive_child_count']),(2,2));self.assertEqual(e['parent_instance_ids'],{'4':[2],'3':[4]})
 def test_shared_root_child_is_deduplicated(self):
  f=Fake();f.arr[0x41f8]=[0x5000];p,e=own_plans(f,0x1000);self.assertEqual(len(p),2);self.assertEqual(e['recursive_child_count'],0)
 def test_child_identity_is_checked(self):
  f=Tree()
  def req(a,name):
   if a==0x6000:raise ObservationError('wrong child identity')
  f.require=req
  with self.assertRaises(ObservationError):own_plans(f,0x1000)
 def test_recursive_complete_capture(self):
  a=json.loads((R/'research/t201_full_capture_recursive_a.json').read_text(encoding='utf-8'));b=json.loads((R/'research/t201_full_capture_recursive_b.json').read_text(encoding='utf-8'));self.assertEqual(a['observation'],b['observation']);p={x['plan_id']:x for x in a['observation']['world']['plans']};self.assertEqual(len(p),6);self.assertEqual(p[4]['vertex_province_ids'],[7944,5097]);self.assertEqual(p[3]['vertex_province_ids'],[2072,7944]);self.assertTrue(all(not x['executing']for x in p.values()));self.assertTrue(all(not any(k in x for k in('type','axis_province_ids','status'))for x in p.values()));self.assertFalse(a['complete_input'])
if __name__=='__main__':unittest.main()
