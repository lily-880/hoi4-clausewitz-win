import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'calling'))
from input_loaded_fields import resolve_building_templates,province_fort_level,building_name_hash
from input_observation import ObservationError
from test_t165_input_loaded_fields import Fixture
class BuildingTests(unittest.TestCase):
 def fixture(self,present=False):
  f=Fixture();module=0x10000000;db=0x1000000;ta=0x1100000;nd=0x1600000
  f.pack(module+0x33dd268,'<Q',db);f.classes[db]='.?AVCBuildingDatabase@@'
  f.pack(db+0x40,'<QII',ta,4,4);f.pack(ta,'<4Q',0x1200000,0x1300000,0x1400000,0x1500000);f.pack(db+0x58,'<QII',nd,3,3)
  for j,name in enumerate(['infrastructure','bunker','coastal_bunker']):
   tp=0x1300000+j*0x100000;f.classes[tp]='.?AVCBuildingTemplate@@';f.pack(tp+8,'<i',[0x2fab,0x577a,0x577b][j]);f.pack(tp+0x2e0,'<i',j+1);f.pack(tp+0x2c4,'<i',0x165);f.put(tp+0x20,b'\1')
   b=name.encode();f.put(nd+j*40,b+b'\0'*(16-len(b)));f.pack(nd+j*40+16,'<QQI',len(b),15,building_name_hash(name))
  pp=0x2000000;st=pp+0x190;f.classes[pp]='.?AVCProvince@@';f.classes[st]='.?AVCBuildingStatus@@';f.pack(st+0x20,'<QII',0x2100000,4,4);f.pack(0x2100000,'<4i',-1,-1,-1,-1)
  if present:
   f.pack(st+0x38,'<QII',0x2300000,1,1);f.pack(0x2300000,'<Q',0x2200000);f.classes[0x2200000]='.?AVCBuilding@@';f.pack(0x2200008,'<i',0x577a);f.pack(0x22001e0,'<Q',0x1400000);f.pack(0x2200040,'<hh',10,10);f.pack(0x2100008,'<i',0)
  return f,module,pp
 def test_actual_lookup_hash_then_match_plus_one(self):
  f,m,p=self.fixture();d,e=resolve_building_templates(f.reader(),m);self.assertEqual(d['bunker'],0x1400000);self.assertEqual(e['loaded_template_count'],4)
 def test_name_hash_mismatch_rejected(self):
  f,m,p=self.fixture();f.pack(0x1600000+40+32,'<I',0)
  with self.assertRaises(ObservationError):resolve_building_templates(f.reader(),m)
 def test_parallel_count_guard(self):
  f,m,p=self.fixture();f.pack(0x100004c,'<I',3)
  with self.assertRaises(ObservationError):resolve_building_templates(f.reader(),m)
 def test_runtime_index_guard(self):
  f,m,p=self.fixture();f.pack(0x14002e0,'<i',9)
  with self.assertRaises(ObservationError):resolve_building_templates(f.reader(),m)
 def test_category_guard(self):
  f,m,p=self.fixture();f.pack(0x14002c4,'<i',999)
  with self.assertRaises(ObservationError):province_fort_level(f.reader(),p,0x1400000)
 def test_absent_zero_is_native_branch_not_guess(self):
  f,m,p=self.fixture();v,e=province_fort_level(f.reader(),p,0x1400000);self.assertEqual(v,0);self.assertIn('native getter',e['status'])
 def test_nonzero_ten(self):
  f,m,p=self.fixture(True);self.assertEqual(province_fort_level(f.reader(),p,0x1400000)[0],10)
 def test_damaged_not_accepted(self):
  f,m,p=self.fixture(True);f.pack(0x2200040,'<hh',10,8);self.assertIsNone(province_fort_level(f.reader(),p,0x1400000)[0])
 def test_overlay_not_accepted(self):
  f,m,p=self.fixture(True);f.pack(0x2200010,'<QII',0x2400000,1,1);f.pack(0x2400000,'<Q',0x2500000);self.assertIsNone(province_fort_level(f.reader(),p,0x1400000)[0])
 def test_map_list_absence_contradiction(self):
  f,m,p=self.fixture(True);f.pack(0x2100008,'<i',-1)
  with self.assertRaises(ObservationError):province_fort_level(f.reader(),p,0x1400000)
 def test_invalid_slot(self):
  f,m,p=self.fixture();f.pack(0x2100008,'<i',999)
  with self.assertRaises(ObservationError):province_fort_level(f.reader(),p,0x1400000)
 def test_backlink_wrong(self):
  f,m,p=self.fixture(True);f.pack(0x22001e0,'<Q',0x1500000)
  with self.assertRaises(ObservationError):province_fort_level(f.reader(),p,0x1400000)
 def test_negative_type_index_rejected_even_empty_map(self):
  f,m,p=self.fixture();f.pack(0x14002e0,'<i',-1);f.pack(p+0x190+0x20,'<QII',0,0,0)
  with self.assertRaises(ObservationError):province_fort_level(f.reader(),p,0x1400000)
 def test_infrastructure_uses_same_proven_absence_branch(self):
  from input_loaded_fields import infrastructure
  f,m,p=self.fixture();state=0x3000000;st=state+0x120;f.classes[state]='.?AVCState@@';f.classes[st]='.?AVCBuildingStatus@@';f.pack(p+0xc0,'<Q',state);f.pack(state+0x58,'<i',271);f.pack(st+0x20,'<QII',0x2100000,4,4)
  value,e=infrastructure(f.reader(),p,0x1300000);self.assertEqual(value,0);self.assertEqual(e['state_id'],271);self.assertIn('native getter',e['status'])
 def test_world_change_rechecked(self):
  f,m,p=self.fixture(True);r=f.reader();province_fort_level(r,p,0x1400000);f.pack(0x2200040,'<hh',9,9)
  with self.assertRaises(ObservationError):r.stable()
if __name__=='__main__':unittest.main()
