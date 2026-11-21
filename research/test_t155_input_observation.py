import copy
import importlib.util
import struct
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('input_observation', Path(__file__).resolve().parents[1] / 'calling/input_observation.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ObservationTests(unittest.TestCase):
    def fixture(self):
        co, arr, ap, pp, vt = 0x100000, 0x200000, 0x300000, 0x400000, 0x500000
        blob = bytearray(0x56c)
        for fmt, off, value in [('<Q',0,vt),('<I',0x18,0x33),('<I',0x1c,1829),
            ('<I',0x28,5010),('<i',0x1e0,44),('<Q',0x1f0,pp),
            ('<i',0x420,12500000),('<i',0x428,5890000),('<i',0x468,100000),
            ('<i',0x4f0,500000000),('<i',0x564,-1)]:
            struct.pack_into(fmt,blob,off,value)
        mem = {co+0x290:struct.pack('<QII',arr,1,1),arr:struct.pack('<Q',ap),ap:bytes(blob),pp+0xa4:struct.pack('<I',5010)}
        return mem, lambda a,n: mem.get(a,b'')[:n], dict(country_ptr=co,player_index=44,carmy_vtable=vt,version_verified=True)
    def test_success_and_honest_omissions(self):
        _,read,kw=self.fixture(); result=m.observe_own_divisions(read,**kw)
        u=result['world']['own_units'][0]
        self.assertEqual(u['organization'],58.9)
        self.assertEqual(u['strength'],{'equipment_ratio':1.0})
        for name in ('supply','in_combat','order','template','leader_id'):
            self.assertNotIn(name,u)
        self.assertNotIn('manpower',u['strength'])
        self.assertFalse(result['_observation']['complete_input'])
        self.assertEqual(len(m.unit_blockers(u)),2)
    def test_explicit_current_never_legacy_max(self):
        _,read,kw=self.fixture();kw['strength420_semantics']='current'
        u=m.observe_own_divisions(read,**kw)['world']['own_units'][0]
        self.assertEqual(u['strength']['current'],125.0)
        self.assertNotIn('max',u['strength'])
    def test_version_required(self):
        _,read,kw=self.fixture(); kw['version_verified']=False
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(read,**kw)
    def test_short_read(self):
        _,_,kw=self.fixture()
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(lambda a,n:b'',**kw)
    def test_non_land_rejected(self):
        mem,read,kw=self.fixture(); b=bytearray(mem[0x300000]);struct.pack_into('<Q',b,0,0x600000);mem[0x300000]=bytes(b)
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(read,**kw)
    def test_wrong_owner_rejected(self):
        mem,read,kw=self.fixture(); b=bytearray(mem[0x300000]);struct.pack_into('<i',b,0x1e0,15);mem[0x300000]=bytes(b)
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(read,**kw)
    def test_province_crosscheck(self):
        mem,read,kw=self.fixture();mem[0x4000a4]=struct.pack('<I',999)
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(read,**kw)
    def test_bounded_count(self):
        mem,read,kw=self.fixture();mem[0x100290]=struct.pack('<QII',0x200000,5000,5000)
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(read,**kw)
    def test_unknown_not_false(self):
        self.assertIn('in_combat: missing required field',m.unit_blockers({}))
    def test_name_only_template_rejected(self):
        self.assertIn('template.template_id: missing required field',m.unit_blockers({'template':{'name':'foo'}}))
    def test_empty_path_not_idle_inference(self):
        self.assertIn('order.type: missing required field',m.unit_blockers({'order':{'path_province_ids':[]}}))
    def test_race_detected(self):
        mem,read,kw=self.fixture();count=0
        def racing(a,n):
            nonlocal count
            if a==0x100290:
                count+=1
                if count==2:return struct.pack('<QII',0x200000,1,0)
            return read(a,n)
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(racing,**kw)
    def test_invalid_equipment(self):
        mem,read,kw=self.fixture();b=bytearray(mem[0x300000]);struct.pack_into('<i',b,0x468,100001);mem[0x300000]=bytes(b)
        with self.assertRaises(m.ObservationError):m.observe_own_divisions(read,**kw)

if __name__=='__main__':unittest.main()
