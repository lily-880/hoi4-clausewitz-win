import sys,json,struct,re
from pathlib import Path
sys.path.insert(0,'calling');from pe import PE
p=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
xs=json.loads(Path('research/t163_key_xrefs.json').read_text(encoding='utf-8'));out=[]
for r in xs:
 if int(r['xref_rva'],16)>=0x120000:continue
 if r['key'] not in ('combat_width','max_strength','max_organisation','supply_consumption'):continue
 xr=int(r['xref_rva'],16)
 # mov edx,[rip+...] occurs exactly 0x13 bytes before this named registration.
 at=xr-0x13;ins=p.read_rva(at,6)
 if not ins or ins[:2]!=b'\x8b\x15':continue
 const=at+6+struct.unpack_from('<i',ins,2)[0];value=struct.unpack('<I',p.read_rva(const,4))[0]
 globalins=p.read_rva(xr+9,7);glob=xr+16+struct.unpack_from('<i',globalins,3)[0]
 row={'key':r['key'],'const_rva':hex(const),'const_u32':hex(value),'registry_rva':hex(glob),'immediate_matches':[]}
 text=next(s for s in p.sections if s.name=='.text');b=p.data[text.raw_ptr:text.raw_ptr+text.raw_size]
 needle=struct.pack('<I',value);start=0
 while True:
  pos=b.find(needle,start)
  if pos<0:break
  if len(row['immediate_matches'])<60:row['immediate_matches'].append({'rva':hex(text.virtual_address+pos),'prefix':b[max(0,pos-4):pos+4].hex()})
  start=pos+4
 out.append(row)
Path('research/t163_stat_tokens.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
