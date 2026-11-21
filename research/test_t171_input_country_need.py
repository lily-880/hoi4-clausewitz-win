import sys,struct,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'calling'))
from input_loaded_fields import official_country_equipment_need_components
from input_observation import ObservationError
from test_t165_input_loaded_fields import Fixture

class Tests(unittest.TestCase):
 def pool(self,f,base,obj,clsname,stride,amount,heap,tp):
  f.classes[obj]='.?AV'+clsname+'@@'
  f.classes[tp]='.?AVCEquipmentType@@'
  name=b'infantry_equipment'
  f.pack(obj+8,'<QII',base,1,1)
  f.pack(tp+0x18,'<Q',heap);f.pack(tp+0x18+16,'<QQ',len(name),31);f.put(heap,name)
  if stride==16:f.pack(base,'<Qq',tp,amount)
  else:f.pack(base,'<Qiiq',tp,0,1,amount)

 def base(self,with_request=True,deploy_deficit=None):
  f=Fixture()
  co,rs,gp,ep,army,tmpl=0x100000,0x200000,0x300000,0x400000,0x500000,0x600000
  dep,res,occ,logi,ops=0x210000,0x220000,0x230000,0x240000,0x250000
  f.classes.update({
   rs:'.?AVCReinforcementStatus@@',gp:'.?AVCArmyReinforcementRequests@@',
   ep:'.?AVCReinforcementRequest@@',army:'.?AVCArmy@@',
   tmpl:'.?AVCReferencedDivisionTemplate@@',
   dep:'.?AVCDeploymentStatus@@',res:'.?AVCCountryResources@@',
   occ:'.?AVCCountryOccupationStatus@@',logi:'.?AVCLogisticsStatus@@',
   ops:'.?AVCCountryOperationManager@@'})
  f.pack(co+0xf70,'<Q',dep);f.pack(co+0xf78,'<Q',rs);f.pack(co+0x11f8,'<Q',res)
  f.pack(co+0xfd0,'<Q',occ);f.pack(co+0xf98,'<Q',logi);f.pack(co+0x15a8,'<Q',ops)
  f.pack(dep+0x60,'<QII',0,0,0)
  f.pack(res+0x758,'<Q',0);f.pack(res+0x764,'<i',0)
  f.pack(occ+0x28,'<QII',0,0,0);f.pack(logi+0x28,'<QII',0,0,0);f.pack(ops+0x10,'<QII',0,0,0)
  f.pack(rs+0x38,'<Q',co)
  if with_request:
   f.pack(rs+0x20,'<QII',0x310000,1,1);f.pack(0x310000,'<Q',gp)
   f.pack(gp+0x20,'<Q',army);f.pack(gp+0x28,'<QII',0x320000,1,1);f.pack(0x320000,'<Q',ep)
   f.pack(army+0x1c,'<i',1835);f.pack(army+0x3b8,'<Q',tmpl)
   self.pool(f,0x410000,ep+0x38,'CEquipmentVariantPool',24,300000,0x800000,0x700000)
   self.pool(f,0x420000,ep+0x78,'CEquipmentArcheTypePool',16,8000000,0x810000,0x710000)
   self.pool(f,0x610000,tmpl+0x120,'CEquipmentArcheTypePool',16,40000000,0x820000,0x720000)
   self.pool(f,0x510000,army+0x348,'CEquipmentVariantPool',24,32000000,0x830000,0x730000)
  else:
   f.pack(rs+0x20,'<QII',0,0,0)
  if deploy_deficit is not None:
   item,holder,inner,dtmpl=0x900000,0x910000,0x920000,0x930000
   f.classes[item]='.?AVCDeployedDivision@@'  # class name is fixture-only; collector does not require it
   # collector does not require item class, only template
   f.classes[dtmpl]='.?AVCReferencedDivisionTemplate@@'
   f.pack(dep+0x60,'<QII',0x940000,1,1);f.pack(0x940000,'<Q',item)
   f.pack(item+0xb8,'<Q',holder);f.pack(holder+0x38,'<Q',inner);f.pack(inner+0x20,'<Q',dtmpl)
   need,cur=deploy_deficit
   self.pool(f,0x950000,item+0x20,'CEquipmentVariantPool',24,cur*100000,0x840000,0x740000)
   self.pool(f,0x960000,dtmpl+0x120,'CEquipmentArcheTypePool',16,need*100000,0x850000,0x750000)
  return f,co,{army:1835} if with_request else {}

 def test_request_need_minus_produced_is_77_not_80_or_2520(self):
  f,co,ids=self.base()
  totals,ev=official_country_equipment_need_components(f.reader(),co,ids)
  self.assertEqual(totals['infantry_equipment'],77)
  self.assertEqual(ev['official_contributors_from_these_components'],[1835])
  self.assertEqual(ev['deployment_plus60_count'],0)
  self.assertEqual(ev['country_resources_11f8_count'],0)
  self.assertEqual(ev['other_component_array_sizes']['occupation']['array_size'],0)
  self.assertTrue(ev['not_fielded_deficit_sum'])

 def test_empty_components_not_fabricated(self):
  f,co,ids=self.base(with_request=False)
  totals,ev=official_country_equipment_need_components(f.reader(),co,ids)
  self.assertEqual(totals,{})
  self.assertEqual(ev['official_contributors_from_these_components'],[])

 def test_deployment_plus60_deficit_added(self):
  f,co,ids=self.base(with_request=True,deploy_deficit=(100,40))
  totals,ev=official_country_equipment_need_components(f.reader(),co,ids)
  self.assertEqual(ev['deployment_plus60_count'],1)
  self.assertEqual(ev['deployment_rows'][0]['deficit']['infantry_equipment']['deficit'],60)
  self.assertEqual(totals['infantry_equipment'],137)

 def test_deployment_plus20_catalog_is_ignored(self):
  f,co,ids=self.base()
  # poison +0x20 with a fake large array; official path must still be +0x60 empty
  f.pack(0x210020,'<QII',0x990000,141,104)
  totals,ev=official_country_equipment_need_components(f.reader(),co,ids)
  self.assertEqual(ev['deployment_plus60_count'],0)
  self.assertEqual(totals['infantry_equipment'],77)

 def test_live_scene_matches_77_and_is_not_emitted_as_demanded(self):
  ev=json.loads((ROOT/'research/t171_f70_plus60_and_requests.json').read_text(encoding='utf-8'))
  self.assertEqual(ev['deployment_plus60_official']['size'],0)
  self.assertEqual(ev['reinforcement_request_contributions'][0]['contribution_need_minus_produced']['infantry_equipment']['need_minus_produced'],77)
  cap_path=ROOT/'research/t171_live_capture.json'
  if cap_path.exists():
   cap=json.loads(cap_path.read_text(encoding='utf-8'))
   self.assertFalse(cap['complete_input'])
   eq=cap['observation']['world']['shortages'].get('equipment')
   self.assertEqual(eq,[{'equipment_type':'train_equipment','stockpile':5}])
   need=cap['evidence']['official_country_need_collection']
   self.assertEqual(need['totals_by_type']['infantry_equipment'],77)
   self.assertEqual(need['official_contributors_from_these_components'],[1835])
   self.assertNotIn('demanded',(eq or [{}])[0])

if __name__=='__main__':
 unittest.main()
