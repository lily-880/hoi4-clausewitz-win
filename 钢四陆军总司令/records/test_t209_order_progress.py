"""Offline fixtures only; no process backend or production capture import."""
import struct, unittest
from fractions import Fraction
from input_observation import ObservationError
from test_t208_order_target import Fixture
from _t209_order_progress import current_edge_progress
class ProgressFixture(Fixture):
 def __init__(self):
  super().__init__();self.cur=0x500000;self.goal=0x600000;self.cg=0x700000;self.ng=0x710000;self.edge=0x800000
  self.classes.update({self.cur:'CProvince',self.goal:'CProvince'});self.provs=[0,self.cur,self.pp,self.goal]
  for p,i in ((self.cur,1),(self.pp,2),(self.goal,3)):self.put(p+0xa4,struct.pack('<i',i))
  self.hdr(0x200,[2,3]);self.put(self.a+8,struct.pack('<i',0));self.put(self.a+0x1f0,struct.pack('<Q',self.cur));self.put(self.cur+0xb8,struct.pack('<Q',self.cg));self.put(self.pp+0xb8,struct.pack('<Q',self.ng));self.put(self.cg+0xd2,b'\x01');self.put(self.ng+0xd2,b'\x01');self.put(self.cg+0x70,struct.pack('<Qii',self.edge,1,1));self.edge_row(2,10000000);self.progress(2500000)
 def edge_row(self,target,distance):
  row=bytearray(48);struct.pack_into('<i',row,8,target);struct.pack_into('<q',row,0x18,distance);self.put(self.edge,row)
 def progress(self,p):self.put(self.a+0x240,struct.pack('<q',p))
 def run_progress(self):return current_edge_progress(self,self.gs,self.co,self.a)
class ProgressProof(unittest.TestCase):
 def setUp(self):self.f=ProgressFixture()
 def reject(self):
  with self.assertRaises(ObservationError):self.f.run_progress()
 def test_positive_first_edge_not_last_goal(self):self.assertEqual(self.f.run_progress(),{'unit_id':392,'eta':{'progress':0.25}})
 def test_exact_native_fixed_truncation(self):
  self.f.edge_row(2,3000000);self.f.progress(1000000);value=self.f.run_progress()['eta']['progress'];ref=int(Fraction(1000000,3000000)*100000)/100000;self.assertEqual(value,ref);self.assertEqual(value,0.33333)
 def test_zero_is_valid_not_promotional_positive(self):self.f.progress(0);self.assertEqual(self.f.run_progress()['eta'],{'progress':0.0})
 def test_finished_edge_boundary(self):self.f.progress(10000000);self.assertEqual(self.f.run_progress()['eta'],{'progress':1.0})
 def test_empty_route_omitted(self):self.f.hdr(0x200,[]);self.assertIsNone(self.f.run_progress())
 def test_queued_branch_rejected(self):self.f.hdr(0x2c0,[3]);self.reject()
 def test_valid_separate_province_target_rejected(self):
  self.f.put(self.f.a+0x1e8,struct.pack('<Q',self.f.pp))
  with self.assertRaisesRegex(ObservationError,'separate province-target'):self.f.run_progress()
 def test_special_distance_branch_rejected(self):self.f.put(self.f.cg+0xd2,b'\x00');self.reject()
 def test_missing_edge_rejected_not_fallback(self):self.f.edge_row(3,10000000);self.reject()
 def test_negative_or_overshoot_rejected(self):
  for v in(-1,10000001):
   with self.subTest(raw=v):self.f.progress(v);self.reject()
 def test_zero_distance_rejected(self):self.f.edge_row(2,0);self.reject()
 def test_current_identity_rejected(self):self.f.put(self.f.cur+0xa4,struct.pack('<i',3));self.reject()
 def test_bad_edge_header_rejected(self):self.f.put(self.f.cg+0x70,struct.pack('<Qii',self.f.edge,0,1));self.reject()
 def test_duplicate_edge_rejected(self):
  row=bytes(self.f.mem[self.f.edge+i]for i in range(48));self.f.put(self.f.edge+48,row);self.f.put(self.f.cg+0x70,struct.pack('<Qii',self.f.edge,2,2));self.reject()
 def test_native_multiply_overflow_rejected(self):
  huge=((1<<63)-1)//100000+1;self.f.edge_row(2,huge);self.f.progress(huge);self.reject()
 def test_unproved_kind_rejected(self):self.f.put(self.f.a+8,struct.pack('<i',3));self.reject()
 def test_bad_next_index_rejected(self):self.f.hdr(0x200,[0,3]);self.reject()
 def test_next_identity_mismatch_rejected(self):self.f.put(self.f.pp+0xa4,struct.pack('<i',99));self.reject()
if __name__=='__main__':unittest.main()
