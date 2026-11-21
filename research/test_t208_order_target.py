"""Offline rejection/positive regressions for t208 narrow goal proof; no live backend."""
import struct,unittest
from input_observation import ObservationError
from _t208_order_target import movement_destination
class Fixture:
 def __init__(self):
  self.gs=0x100000;self.co=0x110000;self.a=0x200000;self.path=0x300000;self.pp=0x400000;self.mem={};self.classes={self.co:'CCountry',self.a:'CArmy',self.pp:'CProvince'};self.units=[self.a];self.provs=[0,0,self.pp];self.put(self.a+0x18,struct.pack('<ii',51,392));self.put(self.a+0x1e8,bytes(8));self.hdr(0x200,[1,2]);self.hdr(0x220,[]);self.hdr(0x2c0,[]);self.put(self.pp+0xa4,struct.pack('<i',2))
 def put(self,a,b):self.mem.update({a+i:v for i,v in enumerate(b)})
 def hdr(self,off,values):
  p=self.path+off*16;self.put(self.a+off,struct.pack('<QII',p if values else 0,len(values),len(values)))
  if values:self.put(p,struct.pack('<'+'i'*len(values),*values))
 def exact(self,a,n):return bytes(self.mem[a+i]for i in range(n))
 def i(self,a):return struct.unpack('<i',self.exact(a,4))[0]
 def q(self,a):return struct.unpack('<Q',self.exact(a,8))[0]
 def array(self,a,bound):
  if a==self.co+0x290:return self.units
  if a==self.gs+0x2b0:return self.provs
  raise AssertionError('unexpected array')
 def require(self,a,name):
  if self.classes.get(a)!=name:raise ObservationError('wrong RTTI')
 def run(self):return movement_destination(self,self.gs,self.co,self.a)
class DestinationProof(unittest.TestCase):
 def setUp(self):self.f=Fixture()
 def rejects(self):
  with self.assertRaises(ObservationError):self.f.run()
 def test_single_step(self):self.f.hdr(0x200,[2]);self.assertEqual(self.f.run(),{'unit_id':392,'target_province_ids':[2]})
 def test_multi_step_last_not_front(self):self.assertEqual(self.f.run()['target_province_ids'],[2])
 def test_empty_omits(self):self.f.hdr(0x200,[]);self.assertIsNone(self.f.run())
 def test_unproved_identity(self):self.f.put(self.f.a+0x18,struct.pack('<i',4713));self.rejects()
 def test_separate_province_target_branch(self):self.f.put(self.f.a+0x1e8,struct.pack('<Q',0x500000));self.rejects()
 def test_queued_full_path(self):self.f.hdr(0x220,[2]);self.rejects()
 def test_queued_command(self):self.f.hdr(0x2c0,[2]);self.rejects()
 def test_bad_header(self):self.f.put(self.f.a+0x200,struct.pack('<QII',self.f.path,1,2));self.rejects()
 def test_bad_goal_bounds(self):self.f.hdr(0x200,[3]);self.rejects()
 def test_goal_identity_mismatch(self):self.f.put(self.f.pp+0xa4,struct.pack('<i',1));self.rejects()
 def test_wrong_army_rtti(self):self.f.classes[self.f.a]='Other';self.rejects()
 def test_foreign_scope(self):self.f.units=[];self.rejects()
if __name__=='__main__':unittest.main()
