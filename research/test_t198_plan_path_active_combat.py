import sys,struct,json,unittest,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'calling'))
from input_loaded_fields import own_active_combats,own_unit_current_combat,own_plans
class Fake:
 def __init__(self):
  self.arr={0x1168:[0x2000],0x2080:[0x3000],0x3098:[0x4000],0x30b0:[0x5000],0x30c8:[0x5000],0x4210:[],0x5210:[],0x1290:[0xa000],0x9268:[0xb000],0xc020:[0xa000],0xd020:[0xe000]}
  self.n={0x300c:411,0x4244:2,0x5244:6,0xa018:51,0xa01c:1831,0xe018:51,0xe01c:1115,0xb018:62,0xb01c:1,0xf0a4:13237}
  self.ptr={0xb028:0xc000,0xb030:0xd000,0xb038:0xf000}
 def require(self,a,name):pass
 def array(self,a,bound):return self.arr.get(a,[])
 def i(self,a):return self.n[a]
 def q(self,a):return self.ptr[a]
 def exact(self,a,n):
  if a in (0x4248,0x5248):return b'\0'
  if a==0x4070:return struct.pack('<QII',0,0,0)
  if a==0x5070:return struct.pack('<QII',0x16000,2,2)
  if a==0x16000:return struct.pack('<II',2072,7944)
  raise AssertionError((a,n))
class Test198(unittest.TestCase):
 def test_three_plan_lists_deduplicate(self):
  plans,ev=own_plans(Fake(),0x1000);self.assertEqual(ev['instance_count'],2);self.assertEqual(plans[1]['vertex_province_ids'],[2072,7944]);self.assertEqual(plans[0]['vertex_province_ids'],[])
 def test_active_combat_secondary_adjust(self):
  d=own_active_combats(Fake(),0x9000,0x1000);self.assertEqual(d,[{'combat_id':1,'province_id':13237,'attacker_unit_ids':[1831],'defender_unit_ids':[1115]}])
 def test_positive_membership_not_empty_false(self):
  self.assertEqual(own_unit_current_combat(Fake(),0x9000,0x1000,1831),{'in_combat':True,'combat_id':1});self.assertEqual(own_unit_current_combat(Fake(),0x9000,0x1000,1829),{})
 def test_foreign_only_combat_omitted(self):
  f=Fake();f.arr[0x1290]=[];self.assertEqual(own_active_combats(f,0x9000,0x1000),[])
 def test_captured_nonempty_and_counts(self):
  d=json.loads((R/'research/t198_validation.json').read_text(encoding='utf-8'));self.assertEqual(d['inventory']['verified'],71);self.assertEqual(d['inventory']['unverified'],45);self.assertEqual(d['inventory']['fields'],116);self.assertEqual(d['inventory']['tables'],14);self.assertEqual(len(d['combats']),2);self.assertFalse(d['allow_post']);self.assertFalse(d['gate_open']);self.assertEqual(d['pause'],1)
if __name__=='__main__':unittest.main()
