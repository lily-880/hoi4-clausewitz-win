import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'calling'))
from input_loaded_fields import own_reinforcement_requests,LoadedReader
from input_observation import ObservationError
from test_t165_input_loaded_fields import Fixture
class Tests(unittest.TestCase):
 def fixture(self):
  f=Fixture();co,rs,gp,ep,army,tmpl=0x100000,0x200000,0x300000,0x400000,0x500000,0x600000
  f.classes.update({rs:'.?AVCReinforcementStatus@@',gp:'.?AVCArmyReinforcementRequests@@',ep:'.?AVCReinforcementRequest@@',army:'.?AVCArmy@@',tmpl:'.?AVCReferencedDivisionTemplate@@'})
  f.pack(co+0xf78,'<Q',rs);f.pack(rs+0x38,'<Q',co);f.pack(rs+0x20,'<QII',0x210000,1,1);f.pack(0x210000,'<Q',gp)
  f.pack(gp+0x20,'<Q',army);f.pack(gp+0x28,'<QII',0x310000,1,1);f.pack(0x310000,'<Q',ep)
  f.pack(army+0x1c,'<i',1835);f.pack(army+0x3b8,'<Q',tmpl)
  def pool(base,obj,clsname,stride,off,tp,amount,heap):
   f.classes[obj]='.?AV'+clsname+'@@';f.classes[tp]='.?AVCEquipmentType@@'
   name=b'infantry_equipment';f.pack(obj+8,'<QII',base,1,1)
   f.pack(tp+0x18,'<Q',heap);f.pack(tp+0x18+16,'<QQ',len(name),31);f.put(heap,name)
   if stride==16:f.pack(base,'<Qq',tp,amount)
   else:f.pack(base,'<Qiiq',tp,0,1,amount)
  pool(0x410000,ep+0x38,'CEquipmentVariantPool',24,16,0x700000,300000,0x800000)
  pool(0x420000,ep+0x78,'CEquipmentArcheTypePool',16,8,0x710000,8000000,0x810000)
  pool(0x610000,tmpl+0x120,'CEquipmentArcheTypePool',16,8,0x720000,40000000,0x820000)
  pool(0x510000,army+0x348,'CEquipmentVariantPool',24,16,0x730000,32000000,0x830000)
  return f,co,{army:1835}
 def test_binds_request_to_own_unit_and_keeps_produced_need(self):
  f,co,ids=self.fixture();rows,e=own_reinforcement_requests(f.reader(),co,ids)
  self.assertEqual(rows[0]['unit_id'],1835)
  self.assertEqual(rows[0]['produced'][0]['amount'],3)
  self.assertEqual(rows[0]['need'][0]['amount'],80)
  self.assertEqual(e['requests'][0]['unit_template_need'][0]['amount'],400)
  self.assertEqual(e['requests'][0]['unit_current'][0]['amount'],320)
  self.assertEqual(e['requests'][0]['unit_template_need'][0]['amount']-e['requests'][0]['unit_current'][0]['amount'],80)
 def test_foreign_or_unknown_army_rejected(self):
  f,co,ids=self.fixture()
  with self.assertRaises(ObservationError):own_reinforcement_requests(f.reader(),co,{})
 def test_country_backlink_rejected(self):
  f,co,ids=self.fixture();f.pack(0x200038,'<Q',0x999)
  with self.assertRaises(ObservationError):own_reinforcement_requests(f.reader(),co,ids)
 def test_empty_status_not_fabricated_demand(self):
  f,co,ids=self.fixture();f.pack(0x200020,'<QII',0,0,0);rows,e=own_reinforcement_requests(f.reader(),co,ids)
  self.assertEqual(rows,[]);self.assertEqual(e['request_count'],0)
 def test_negative_need_rejected(self):
  f,co,ids=self.fixture();f.pack(0x420000,'<Qq',0x710000,-1)
  with self.assertRaises(ObservationError):own_reinforcement_requests(f.reader(),co,ids)
 def test_live_request_not_treated_as_national_total(self):
  import json
  root=Path(__file__).resolve().parents[1]
  cap=json.loads((root/'research/t170_live_capture.json').read_text(encoding='utf-8')) if (root/'research/t170_live_capture.json').exists() else None
  ev=json.loads((root/'research/t170_own_unit_equipment_deficits.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['sum_of_own_unit_deficits']['infantry_equipment'],2520)
  self.assertTrue(ev['active_request_need_80_is_not_country_sum'])
  self.assertEqual(len(ev['units_with_positive_deficit']),19)
  if cap:
   req=cap['evidence']['reinforcement_request_collection']['requests']
   self.assertEqual(len(req),1);self.assertEqual(req[0]['unit_id'],1835)
   self.assertEqual(req[0]['need'][0]['amount'],80)
   self.assertNotIn('demanded',cap['observation']['world']['shortages'].get('equipment',[{}])[0] if cap['observation']['world']['shortages'].get('equipment') else {'equipment_type':'train_equipment'})
if __name__=='__main__':unittest.main()
