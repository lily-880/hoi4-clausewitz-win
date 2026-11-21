import os,sys,re,struct,json,bisect
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0';os.environ['CLAUSEWITZ_ALLOW_POST']='0';sys.path.insert(0,'calling')
from pe import PE
from mem import Proc,find_pid
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
p=Proc(find_pid('hoi4.exe'));pe=PE(p.image_path);p.close()
keys=json.loads(Path('research/t163_static_keys.json').read_text(encoding='utf-8'))
wanted={int(v,16):name for name,vs in keys.items() for v in vs}
text=next(s for s in pe.sections if s.name=='.text');blob=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
pdata=next(s for s in pe.sections if s.name=='.pdata');pd=pe.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size]
functions=[struct.unpack_from('<III',pd,o)[:2] for o in range(0,len(pd)-11,12)];starts=[x[0] for x in functions]
cs=Cs(CS_ARCH_X86,CS_MODE_64)
out=[];cache={}
for m in re.finditer(rb'[\x48\x4c][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}',blob,re.S):
 rva=text.virtual_address+m.start();target=rva+7+struct.unpack_from('<i',m.group(),3)[0]
 if target not in wanted:continue
 j=bisect.bisect_right(starts,rva)-1
 if j<0:continue
 start,end=functions[j]
 if not start<=rva<end:continue
 if start not in cache:
  raw=pe.read_rva(start,min(end-start,1000000)) or b''
  cache[start]=[{'rva':hex(i.address),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(raw,start)]
 inst=cache[start]
 window=[x for x in inst if rva-100<=int(x['rva'],16)<=rva+180]
 out.append({'key':wanted[target],'string_rva':hex(target),'xref_rva':hex(rva),'function':hex(start),'function_end':hex(end),'instructions':window})
Path('research/t163_key_xrefs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('COUNTS', {key:sum(x['key']==key for x in out) for key in keys})
for r in out:
 if r['key'] in ('combat_width','max_strength','max_organisation','supply_consumption','attack_skill','defense_skill','planning_skill','logistics_skill'):
  print(json.dumps(r,indent=2))
