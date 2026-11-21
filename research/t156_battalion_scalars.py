import sys,json,struct,collections
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,u64,cls,inspect
out={'subunit_definitions':[],'province_terrain':[],'areas':[]}
try:
 a=json.loads(Path('research/t156_template_map_links.json').read_text(encoding='utf-8'));seen=set()
 for t in a['templates']:
  for s in t['battalion_slots']+t['support_slots']:
   sp=int(s['ptr'],16)
   if sp in seen or s['class']!='.?AVCSubUnitDefinition@@':continue
   seen.add(sp);r=inspect(sp,0x690);r['name']=s['name18'];out['subunit_definitions'].append(r)
 for r in a['province_links']:
  tp=u64(int(r['b8']['ptr'],16)+0xa8)
  b=P.read(tp+0x18,32);size,cap=struct.unpack_from('<QQ',b,16)
  raw=b[:size] if cap<=15 else P.read(struct.unpack_from('<Q',b)[0],size)
  out['province_terrain'].append({'province_id':r['province_id'],'terrain':raw.decode('utf-8'),'terrain_class':cls(tp),'definition_link':'CProvince+0xB8 -> +0xA8 CTerrainType -> name+0x18'})
 for r in a['area_objects']:
  aa=int(r['object']['ptr'],16);out['areas'].append({'offset':r['offset'],'class':cls(aa),'prefix_words':{hex(i):hex(P.u64(aa+i)) for i in range(0,0x90,8)}})
 Path('research/t156_battalion_scalars.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print('TERRAIN',out['province_terrain']);print('AREAS',out['areas'])
 for r in out['subunit_definitions']:
  b=bytes.fromhex(r['hex']);vals=[]
  for o in range(0x100,len(b)-3,4):
   v=struct.unpack_from('<i',b,o)[0]
   if v in (150000,200000,2500000,2000000,3000000,100000000,50000000,4500000,6000000,7000000):vals.append((hex(o),v/100000))
  print('SUBDEF',r['name'],vals)
finally:P.close()
