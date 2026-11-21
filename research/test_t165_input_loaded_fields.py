import sys,struct,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'calling'))
from input_loaded_fields import LoadedReader,battalion_width,infrastructure,country_tag,victory_points
from input_observation import ObservationError
class Fixture:
 def __init__(self):self.mem={};self.classes={}
 def put(self,a,b):self.mem.update((a+j,c) for j,c in enumerate(b))
 def pack(self,a,f,*v):self.put(a,struct.pack(f,*v))
 def read(self,a,n):return bytes(self.mem.get(a+j,0) for j in range(n))
 def reader(self):return LoadedReader(self.read,self.classes.get)
 def infra(self,level=None):
  self.pack(0x900c0,'<Q',0x80000);self.classes[0x80000]='.?AVCState@@';self.pack(0x80058,'<i',271)
  self.pack(0x80158,'<QII',0xb0000,int(level is not None),int(level is not None))
  if level is not None:
   self.pack(0xb0000,'<Q',0xa0000);self.classes[0xa0000]='.?AVCBuilding@@';self.pack(0xa0008,'<i',0x2fab);self.pack(0xa0040,'<hh',*level)
  return infrastructure(self.reader(),0x90000)
class Tests(unittest.TestCase):
 def test_width_qword_fixed(self):
  f=Fixture();f.classes[0x70000]='.?AVCSubUnitDefinition@@';f.pack(0x70058,'<q',150000);self.assertEqual(battalion_width(f.reader(),0x70000),1.5)
 def test_negative_width(self):
  f=Fixture();f.classes[0x70000]='.?AVCSubUnitDefinition@@';f.pack(0x70058,'<q',-1)
  with self.assertRaises(ObservationError):battalion_width(f.reader(),0x70000)
 def test_wrong_class(self):
  with self.assertRaises(ObservationError):battalion_width(Fixture().reader(),0x70000)
 def test_present_infra(self):self.assertEqual(Fixture().infra((2,2))[0],2)
 def test_nonempty_level_overlay_not_base_level(self):
  f=Fixture();f.infra((2,2));f.pack(0xa0010,'<QII',0xc0000,1,1);f.pack(0xc0000,'<Q',0xd0000)
  self.assertIsNone(infrastructure(f.reader(),0x90000)[0])
 def test_absent_not_zero(self):self.assertIsNone(Fixture().infra()[0])
 def test_damaged_not_guessed(self):self.assertIsNone(Fixture().infra((2,1))[0])
 def test_mutation(self):
  f=Fixture();r=f.reader();r.i(0x12340);f.pack(0x12340,'<i',1)
  with self.assertRaises(ObservationError):r.stable()
 def test_array_bounds(self):
  f=Fixture();f.pack(0x12340,'<QII',0x20000,99999,99999)
  with self.assertRaises(ObservationError):f.reader().array(0x12340,128)
 def test_sso_no_first_letter_loss(self):
  f=Fixture();f.put(0x12340,b'desert_fox'+b'\0'*7);f.pack(0x12350,'<QQ',10,15);self.assertEqual(f.reader().string(0x12340),'desert_fox')
 def test_heap_no_first_letter_loss(self):
  f=Fixture();s=b'politically_connected';f.pack(0x12340,'<Q',0x20000);f.pack(0x12350,'<QQ',len(s),31);f.put(0x20000,s);self.assertEqual(f.reader().string(0x12340),s.decode())
 def test_live_schema(self):
  import jsonschema
  cap=json.loads((ROOT/'research/t165_live_capture.json').read_text(encoding='utf-8'));s=json.loads((ROOT/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'));w=cap['observation']['world'];self.assertEqual(len(w['leaders']),20)
  for l in w['leaders']:jsonschema.validate(l,{'$ref':'#/$defs/Leader','$defs':s['$defs']})
  for u in w['own_units']:jsonschema.validate(u['template'],{'$ref':'#/$defs/Template','$defs':s['$defs']})
  self.assertEqual(cap['evidence']['leader_collection']['display_name_pointer_links'],20);self.assertNotIn('assigned_to',w['leaders'][0]);self.assertNotIn('visible_units',w);self.assertFalse(cap['complete_input'])

 def test_victory_points_integer(self):
  f=Fixture();f.classes[0x90000]='.?AVCProvince@@';f.pack(0x90038,'<i',5);self.assertEqual(victory_points(f.reader(),0x90000),{'value':5})
 def test_victory_points_zero_valid(self):
  f=Fixture();f.classes[0x90000]='.?AVCProvince@@';self.assertEqual(victory_points(f.reader(),0x90000),{'value':0})
 def test_victory_points_name(self):
  f=Fixture();f.classes[0x90000]='.?AVCProvince@@';f.put(0x90040,b'Custom VP');f.pack(0x90050,'<QQ',9,15);self.assertEqual(victory_points(f.reader(),0x90000)['name'],'Custom VP')
 def tag_fixture(self):
  f=Fixture();gs=0xd0000;co=0x10000;f.pack(gs+0x358,'<QII',0xc0000,45,45);f.pack(gs+0x310,'<QII',0xe0000,45,45);f.pack(0xe0000+44*8,'<Q',co);f.pack(co+8,'<i',44);f.put(0xc0000+44*32,b'ETH');f.pack(0xc0000+44*32+16,'<QQ',3,15);return f,gs,co
 def test_country_tag_current_table(self):
  f,gs,co=self.tag_fixture();self.assertEqual(country_tag(f.reader(),gs,44,co),'ETH')
 def test_country_tag_reverse_index(self):
  f,gs,co=self.tag_fixture();f.pack(co+8,'<i',45)
  with self.assertRaises(ObservationError):country_tag(f.reader(),gs,44,co)
 def test_country_tag_invalid(self):
  f,gs,co=self.tag_fixture();f.put(0xc0000+44*32,b'eth')
  with self.assertRaises(ObservationError):country_tag(f.reader(),gs,44,co)

if __name__=='__main__':unittest.main()
