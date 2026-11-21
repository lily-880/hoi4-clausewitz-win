import copy,json,unittest
from pathlib import Path
from t218_captured_calendar_replay import replay,native_text,month_partition,native_div24,native_div365,native_div8760,EPOCH,MONTHS

def synthetic(y,m,d,h):
 # Synthetic OFFLINE unit-test operands, never game samples or game writes.
 return EPOCH+((365*y+sum(MONTHS[:m-1])+d-1)*24+h-1)

class CapturedCalendarTests(unittest.TestCase):
 def setUp(self):self.p=json.loads((Path(__file__).parent/'t218_native_GameTime_bridge.json').read_text())
 def test_actual_positive_control(self):self.assertEqual(replay(60781105,self.p),{'year':1938,'month':6,'day':26,'hour':2})
 def test_actual_native_padding(self):self.assertEqual(native_text(60781105,self.p),'1938.06.26.02')
 def test_magic_div24(self):
  for n in [0,1,23,24,25,8759,8760,16981105,2**31-1-EPOCH]:self.assertEqual(native_div24(n),n//24)
 def test_magic_div365(self):
  for n in [0,1,364,365,366,707546,(2**31-1-EPOCH)//24]:self.assertEqual(native_div365(n),n//365)
 def test_magic_div8760(self):
  for n in [0,1,8759,8760,8761,16981105,2**31-1-EPOCH]:self.assertEqual(native_div8760(n),n//8760)
 def test_first_AD_year(self):self.assertEqual(replay(EPOCH+8760,self.p),{'year':1,'month':1,'day':1,'hour':1})
 def test_native_hour24(self):self.assertEqual(replay(synthetic(1938,6,26,24),self.p)['hour'],24)
 def test_next_day_hour1(self):self.assertEqual(replay(synthetic(1938,6,26,24)+1,self.p),{'year':1938,'month':6,'day':27,'hour':1})
 def test_fixed_Feb28_even_1936(self):self.assertEqual(replay(synthetic(1936,2,28,24)+1,self.p),{'year':1936,'month':3,'day':1,'hour':1})
 def test_year_boundary(self):self.assertEqual(replay(synthetic(1938,12,31,24)+1,self.p),{'year':1939,'month':1,'day':1,'hour':1})
 def test_reject_preAD(self):
  with self.assertRaises(ValueError):replay(EPOCH,self.p)
 def test_reject_nonsigned32_or_noninteger(self):
  for bad in [-1,2**31,True,60781105.0]:
   with self.assertRaises(ValueError):replay(bad,self.p)
 def test_reject_wrong_native_format(self):
  self.p['format_literal']='%d.%d.%d.%d'
  with self.assertRaises(ValueError):replay(60781105,self.p)
 def test_reject_Gregorian_leap_table(self):
  self.p['month_lengths'][1]=29
  with self.assertRaises(ValueError):replay(60781105,self.p)
 def test_reject_unresolved_flow(self):
  self.p['flows']['month']['unresolved_edges'].append({'address':'unknown'})
  with self.assertRaises(ValueError):replay(60781105,self.p)
 def test_reject_missing_epoch_anchor(self):
  self.p['flows']['month']['asm'].remove('17f7f8 sub edx, 0x29c55c0')
  with self.assertRaises(ValueError):replay(60781105,self.p)
 def test_month_partition_not_battle_or_day_id(self):self.assertEqual(month_partition(synthetic(1938,6,1,1),self.p),month_partition(synthetic(1938,6,30,24),self.p))
 def test_month_partition_next_month(self):self.assertEqual(month_partition(synthetic(1938,7,1,1),self.p)-month_partition(synthetic(1938,6,30,24),self.p),1)
 def test_reject_changed_cached_year(self):
  self.p['guard']['year']+=1;self.p['after']['year']+=1
  with self.assertRaises(ValueError):replay(60781105,self.p)
 def test_reject_other_build(self):
  self.p['version']='1.19.6'
  with self.assertRaises(ValueError):replay(60781105,self.p)
if __name__=='__main__':unittest.main()
