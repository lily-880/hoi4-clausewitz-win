import sys,json,struct
from pathlib import Path
sys.path.insert(0,'research')
from t156_objects import P,PEFILE,cls,u64
from gamestate import _rtti_name_from_vtable
out={'vtable_function_classes':[],'scalars':[]}
try:
 ar=json.loads(Path('research/t156_battalion_scalars.json').read_text(encoding='utf-8'))['subunit_definitions']
 for r in ar:
  a=int(r['ptr'],16);b=P.read(a,0x450);out['scalars'].append({'name':r['name'],'i32_310_440':{hex(o):struct.unpack_from('<i',b,o)[0] for o in range(0x310,0x440,4)},'vtable_rva':hex(u64(a)-P.base),'functions':[hex(u64(u64(a)+i*8)-P.base) for i in range(12)]})
 for fn in (0x14c9380,0x14db9d0,0x148bdc0):
  needle=struct.pack('<Q',PEFILE.image_base+fn);hits=[]
  for sec in PEFILE.sections:
   if sec.name!='.rdata':continue
   data=PEFILE.data[sec.raw_ptr:sec.raw_ptr+sec.raw_size];start=0
   while True:
    pos=data.find(needle,start)
    if pos<0:break
    rva=sec.virtual_address+pos;found=[]
    for back in range(0,128*8,8):
     try:n=_rtti_name_from_vtable(PEFILE,rva-back)
     except Exception:n=None
     if n and n.startswith(('.?AV','.?AU')) and n.endswith('@@'):found.append({'vtable':hex(rva-back),'class':n,'slot':hex(back)});break
    hits.append({'rva':hex(rva),'class_candidates':found});start=pos+8
  out['vtable_function_classes'].append({'function':hex(fn),'hits':hits})
 Path('research/t163_subunit_layout.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 print(json.dumps(out,indent=2))
finally:P.close()
