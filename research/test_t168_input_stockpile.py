import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'calling'))
from input_loaded_fields import LoadedReader,own_equipment_stockpile
from input_observation import ObservationError
class StockpileTests(unittest.TestCase):
 def fixture(self):
  co,ps,tp,vp,definition,ta,va=0x100000,0x200000,0x300000,0x400000,0x500000,0x600000,0x700000
  pool=ps+0x200
  names={ps:'CProductionStatus',pool:'CEquipmentVariantPool',tp:'CEquipmentType',vp:'CEquipmentVariant',definition:'CEquipmentType'}
  mem={a:struct.pack('<Q',0x900000) for a in names}
  mem.update({co+0xf68:struct.pack('<Q',ps),pool+8:struct.pack('<QII',ta,1,1),pool+0x20:struct.pack('<QII',va,1,1),ta:struct.pack('<Qiiq',tp,0,1,500000),va:struct.pack('<Qq',vp,500000),vp+0x3f0:struct.pack('<Q',definition),definition+0x538:struct.pack('<Q',tp),tp+0x18:b'train_equipment'+b'\0'+struct.pack('<QQ',15,15)})
  def read(a,n):
   for base,b in sorted(mem.items(),reverse=True):
    if base<=a and a+n<=base+len(b):return b[a-base:a-base+n]
   return b''
  return mem,LoadedReader(read,lambda a:'.?AV'+names.get(a,'Wrong')+'@@'),co
 def test_current_five_and_metadata_not_amount(self):
  _,r,co=self.fixture();rows,e=own_equipment_stockpile(r,co);self.assertEqual(rows,[{'equipment_type':'train_equipment','stockpile':5}]);self.assertEqual(e['buckets'][0]['begin'],0);self.assertEqual(e['buckets'][0]['variant_count'],1);self.assertGreater(r.stable(),0)
 def test_fractional_not_guessed_integer(self):
  mem,r,co=self.fixture();mem[0x600000]=struct.pack('<Qiiq',0x300000,0,1,550000);mem[0x700000]=struct.pack('<Qq',0x400000,550000);rows,_=own_equipment_stockpile(r,co);self.assertNotIn('stockpile',rows[0])
 def test_negative_rejected(self):
  mem,r,co=self.fixture();mem[0x600000]=struct.pack('<Qiiq',0x300000,0,1,-1)
  with self.assertRaises(ObservationError):own_equipment_stockpile(r,co)
 def test_total_mismatch_rejected(self):
  mem,r,co=self.fixture();mem[0x700000]=struct.pack('<Qq',0x400000,400000)
  with self.assertRaises(ObservationError):own_equipment_stockpile(r,co)
 def test_type_backlink_rejected(self):
  mem,r,co=self.fixture();mem[0x500538]=struct.pack('<Q',0x123456)
  with self.assertRaises(ObservationError):own_equipment_stockpile(r,co)
 def test_range_rejected(self):
  mem,r,co=self.fixture();mem[0x600000]=struct.pack('<Qiiq',0x300000,0,2,500000)
  with self.assertRaises(ObservationError):own_equipment_stockpile(r,co)
 def test_uncovered_variant_rejected(self):
  mem,r,co=self.fixture();mem[0x600000]=struct.pack('<Qiiq',0x300000,0,0,0)
  with self.assertRaises(ObservationError):own_equipment_stockpile(r,co)
 def test_wrong_typed_root_rejected(self):
  _,r,co=self.fixture();r.class_name=lambda a:'.?AVWrong@@'
  with self.assertRaises(ObservationError):own_equipment_stockpile(r,co)
 def test_stability_after_quantity_change(self):
  mem,r,co=self.fixture();own_equipment_stockpile(r,co);mem[0x700000]=struct.pack('<Qq',0x400000,600000)
  with self.assertRaises(ObservationError):r.stable()
 def test_empty_stock_not_fabricated_type(self):
  mem,r,co=self.fixture();mem[0x200208]=struct.pack('<QII',0,0,0);mem[0x200220]=struct.pack('<QII',0,0,0);rows,e=own_equipment_stockpile(r,co);self.assertEqual(rows,[]);self.assertEqual(e['variant_count'],0)
class HpSafetyTests(unittest.TestCase):
 def test_historical_max_mode_forbidden(self):
  import input_observation as m
  with self.assertRaises(ObservationError):m.observe_own_divisions(lambda a,n:b'',country_ptr=1,player_index=44,carmy_vtable=1,version_verified=True,strength420_semantics='historical_max')
if __name__=='__main__':unittest.main()
