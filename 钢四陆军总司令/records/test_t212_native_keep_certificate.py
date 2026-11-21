import copy,json,unittest
from pathlib import Path
from t211_native_keep_certificate import load,ongoing as previous
from t212_native_keep_certificate import ongoing
Q=Path(__file__).resolve().parent
class ScopedExtendedHandleTests(unittest.TestCase):
    def setUp(self):
        self.d=load(Q);self.p=json.loads((Q/'t212_session_extended_handle_revalidation.json').read_text(encoding='utf-8'));self.ptr=self.d[0]['combats'][1]['ptr']
    def result(self):return ongoing(self.d,self.ptr,self.p)
    def test_actual3072_positive(self):
        r=self.result();self.assertEqual((r['combat_id'],r['phase']),(3072,'ongoing'));self.assertEqual([s['average_raw428']for s in r['native_side_certificates']],[2503180,1417769])
    def test_default_and_original_remain_closed(self):self.assertIsNone(ongoing(self.d,self.ptr));self.assertIsNone(previous(self.d,self.ptr))
    def test_existing_two_unchanged(self):
        for i in (0,2):
            with self.subTest(index=i):self.assertEqual(ongoing(self.d,self.d[0]['combats'][i]['ptr'],self.p),previous(self.d,self.d[0]['combats'][i]['ptr']))
    def test_identity_corruption_rejected(self):
        for key,val in [('COL_offset',0),('RTTI','.?AVCArmyGroup@@'),('complete_object','0x1234'),('secondary_vtable_rva','0x0'),('resolved_secondary','0x1234'),('registry_global_rva','0x34ffbf8')]:
            with self.subTest(field=key):
                p=copy.deepcopy(self.p);p['cases'][2][key]=val;self.assertIsNone(ongoing(self.d,self.ptr,p))
    def test_session_mismatch(self):self.p['guard']['hour_tick']+=1;self.assertIsNone(self.result())
    def test_wrong_extended_key(self):self.p['cases'][2]['trace'][0]['key_id']+=1;self.assertIsNone(self.result())
    def test_other_unproved_handle(self):
        for field,value in [('handle_type',4714),('army_id',4653)]:
            with self.subTest(field=field):
                d=copy.deepcopy(self.d);d[3]['rows'][1]['side_handles'][0][field]=value;self.assertIsNone(ongoing(d,self.ptr,self.p))
    def test_early_probe_stop(self):self.p['cases'][2]['trace'][0]['stored_distance']=0;self.assertIsNone(self.result())
    def test_missing_collision_control(self):self.p['cases'][1]['trace'].pop(0);self.assertIsNone(self.result())
    def test_forced_end_not_bypassed(self):self.d[0]['combats'][1]['sides'][0]['flagD9']=1;self.assertIsNone(self.result())
    def test_native_stat_limits_not_bypassed(self):
        for field in ['raw420','raw428']:
            with self.subTest(field=field):
                d=copy.deepcopy(self.d)
                for u in d[0]['combats'][1]['sides'][0]['members']:u[field]=0
                self.assertIsNone(ongoing(d,self.ptr,self.p))
    def test_wrong_native_leaf_rejected(self):
        ptr=self.d[0]['combats'][1]['sides'][0]['members'][0]['ptr'];self.d[2]['unit_bindings'][ptr]['slots']['248']=0;self.assertIsNone(self.result())
    def test_member_iteration_order_irrelevant(self):
        expected=self.result();self.d[0]['combats'][1]['sides'][0]['members'].reverse();self.assertEqual(self.result(),expected)
if __name__=='__main__':unittest.main(verbosity=2)
