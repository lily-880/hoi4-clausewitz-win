import unittest,struct,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'calling'));sys.path.insert(0,str(ROOT/'research'))
from input_loaded_fields import unit_current_manpower,country_available_manpower,unit_hp
from input_observation import ObservationError
from test_t165_input_loaded_fields import Fixture
class ManpowerTests(unittest.TestCase):
 def army(self,current,need):
  f=Fixture();ap=0x10000;mp=ap+0x3d0;f.classes[mp]='.?AVCArmyManpower@@';f.pack(mp+0x48,'<Q',ap)
  for j,(table,rows) in enumerate([(mp+8,current),(mp+0x28,need)]):
   data=0x20000+j*0x1000;f.pack(table+8,'<QII',data,len(rows),len(rows));f.put(data,b''.join(struct.pack('<ii',*r) for r in rows))
  return f,ap
 def country(self):
  f=Fixture();co=0x10000;mp=co+0x328;st=0x30000;pool=st+0x838;f.classes[mp]='.?AVCCountryManpower@@';f.classes[st]='.?AVCState@@';f.classes[pool]='.?AVCStateManpower@@';f.pack(mp+8,'<ii',44,10);f.pack(mp+0x10,'<q',450000);f.pack(co+0x460,'<QII',0x20000,1,1);f.pack(0x20000,'<Q',st);f.pack(pool+8,'<Q',st);f.pack(pool+0x10,'<i',70601);f.pack(st+0x58,'<i',271);return f,co
 def test_current_not_need(self):
  f,a=self.army([(44,5000)],[(44,6000)]);v,e=unit_current_manpower(f.reader(),a);self.assertEqual((v,e['engine_need_total'],e['engine_missing_formula']),(5000,6000,1000))
 def test_multiple_nationalities(self):
  f,a=self.army([(44,3000),(1,500)],[(44,4000)]);self.assertEqual(unit_current_manpower(f.reader(),a)[0],3500)
 def test_current_not_capped_or_missing_negative(self):
  f,a=self.army([(44,7000)],[(44,6000)]);v,e=unit_current_manpower(f.reader(),a);self.assertEqual((v,e['engine_missing_formula']),(7000,0))
 def test_zero_current(self):
  f,a=self.army([],[(44,4000)]);self.assertEqual(unit_current_manpower(f.reader(),a)[0],0)
 def test_negative_count_rejected(self):
  f,a=self.army([(44,-1)],[(44,4000)])
  with self.assertRaises(ObservationError):unit_current_manpower(f.reader(),a)
 def test_bad_army_backlink(self):
  f,a=self.army([(44,4)],[(44,4)]);f.pack(a+0x418,'<Q',0)
  with self.assertRaises(ObservationError):unit_current_manpower(f.reader(),a)
 def test_country_sum_not_ratio(self):
  f,c=self.country();v,e=country_available_manpower(f.reader(),c,44);self.assertEqual(v,70611);self.assertEqual(e['central_current'],10)
 def test_country_index_mismatch(self):
  f,c=self.country()
  with self.assertRaises(ObservationError):country_available_manpower(f.reader(),c,45)
 def test_state_backlink_required(self):
  f,c=self.country();f.pack(0x30840,'<Q',0)
  with self.assertRaises(ObservationError):country_available_manpower(f.reader(),c,44)
 def test_actual_live_current_and_available(self):
  cap=json.loads((ROOT/'research/t167_live_capture.json').read_text(encoding='utf-8'));w=cap['observation']['world'];self.assertEqual(sum(x['strength']['manpower'] for x in w['own_units']),105000);self.assertEqual(w['shortages']['manpower']['available'],304556);self.assertNotIn('needed',w['shortages']['manpower']);self.assertNotIn('equipment',w['shortages'])

 def hp(self,current,maximum):
  f=Fixture();a=0x10000;st=0x40000;f.classes[st]='.?AVCSubUnitDefinition@@';f.pack(a+0x138,'<Q',st);f.pack(a+0x420,'<q',current);f.pack(st+0x288,'<q',maximum);return f,a
 def test_hp_current_separate_from_max(self):
  f,a=self.hp(10000000,12500000);self.assertEqual(unit_hp(f.reader(),a)[:2],(100.0,125.0))
 def test_hp_zero_current_valid(self):
  f,a=self.hp(0,12500000);self.assertEqual(unit_hp(f.reader(),a)[:2],(0.0,125.0))
 def test_hp_max_engine_minimum(self):
  f,a=self.hp(0,0);self.assertEqual(unit_hp(f.reader(),a)[1],0.001)
 def test_hp_current_above_max_rejected(self):
  f,a=self.hp(12600000,12500000)
  with self.assertRaises(ObservationError):unit_hp(f.reader(),a)
 def test_hp_negative_rejected(self):
  f,a=self.hp(-1,12500000)
  with self.assertRaises(ObservationError):unit_hp(f.reader(),a)

if __name__=='__main__':unittest.main()
