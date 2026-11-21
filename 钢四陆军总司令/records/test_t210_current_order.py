import struct, unittest
from input_observation import ObservationError
from _t210_current_order import current_strategic_order
A,C,G,P,D=0x100000,0x200000,0x300000,0x400000,0x500000
class Fake:
    def __init__(self):
        self.ints={A+0x18:51,A+0x1c:462,A+8:0,D+0xa4:17,P:17}
        self.ptrs={A+0x1e8:0,A+0x2f8:0}
        self.arrays={C+0x290:[A],A+0x1a8:[],G+0x2b0:[0]*17+[D]}
        self.data={A+0x2af:b'\x01',A+0x24c:b'\x00',A+0x24d:b'\x00',A+0x2ae:b'\x00',A+0x200:struct.pack('<QII',P,1,1),A+0x220:struct.pack('<QII',0,0,0),A+0x2c0:struct.pack('<QII',0,0,0)}
    def require(self,a,n):
        if {A:'CArmy',C:'CCountry',D:'CProvince'}.get(a)!=n:raise ObservationError('class')
    def array(self,a,limit):
        v=self.arrays[a]
        if len(v)>limit:raise ObservationError('count')
        return v
    def i(self,a):return self.ints[a]
    def q(self,a):return self.ptrs[a]
    def exact(self,a,n):
        v=self.data[a]
        if len(v)!=n:raise ObservationError('width')
        return v
class CurrentStrategicOrder(unittest.TestCase):
    def setUp(self):self.r=Fake()
    def run_reader(self):return current_strategic_order(self.r,G,C,A)
    def reject(self):
        with self.assertRaises(ObservationError):self.run_reader()
    def test_positive_current_flag(self):self.assertEqual(self.run_reader(),{'unit_id':462,'order':{'type':'strategic_redeploy'}})
    def test_inactive_omitted(self):self.r.data[A+0x2af]=b'\x00';self.assertIsNone(self.run_reader())
    def test_no_route_omitted(self):self.r.data[A+0x200]=struct.pack('<QII',0,0,0);self.assertIsNone(self.run_reader())
    def test_future_queue_rejected(self):self.r.data[A+0x2c0]=struct.pack('<QII',P,1,1);self.reject()
    def test_full_path_rejected(self):self.r.data[A+0x220]=struct.pack('<QII',P,1,1);self.reject()
    def test_combat_rejected(self):self.r.arrays[A+0x1a8]=[0x999999];self.reject()
    def test_support_rejected(self):self.r.ptrs[A+0x1e8]=D;self.reject()
    def test_transport_rejected(self):self.r.ptrs[A+0x2f8]=D;self.reject()
    def test_retreat_rejected(self):self.r.data[A+0x24c]=b'\x01';self.reject()
    def test_withdraw_rejected(self):self.r.data[A+0x24d]=b'\x01';self.reject()
    def test_exile_rejected(self):self.r.data[A+0x2ae]=b'\x01';self.reject()
    def test_bad_flag_rejected(self):self.r.data[A+0x2af]=b'\x02';self.reject()
    def test_not_own_rejected(self):self.r.arrays[C+0x290]=[];self.reject()
    def test_bad_handle_rejected(self):self.r.ints[A+0x18]=4713;self.reject()
    def test_wrong_kind_rejected(self):self.r.ints[A+8]=1;self.reject()
    def test_priority_not_consulted(self):
        for priority in (0,1,2,3,99):
            with self.subTest(priority=priority):self.r.ints[A+0x248]=priority;self.assertEqual(self.run_reader()['order']['type'],'strategic_redeploy')
    def test_queued_action_never_implies_current_flag(self):self.r.data[A+0x2af]=b'\x00';self.r.data[A+0x2c0]=struct.pack('<QII',P,1,1);self.assertIsNone(self.run_reader())
    def test_invalid_path_count_rejected(self):self.r.data[A+0x200]=struct.pack('<QII',P,0,1);self.reject()
if __name__=='__main__':unittest.main()
