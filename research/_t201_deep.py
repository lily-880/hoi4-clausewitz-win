from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
cs.detail=False
vt=0x29d6d98
out={'army_vmethods':{}}
for slot in (0x158,0x180):
 a=struct.unpack('<Q',p.read_rva(vt+slot,8))[0]-0x140000000;out['army_vmethods'][hex(slot)]={'rva':hex(a),'asm':clip(a)}
for a in (0xcd0480,0xce4cd0,0xcd8820,0x1744d30,0x1489550):
 ls=clip(a);out[hex(a)]={'begin':ls[:80]}
 if a==0xcd8820:out[hex(a)]['supply_reads']=[s for s in ls if any(x in s for x in ('r14 + 0x20','r14 + 0x28','r14 + 0x30','r14 + 0x40','r14 + 0x610','0xcd8d','0xc5'))]
 if a==0x1489550:out[hex(a)]['all']=ls
# Functions that access idler +a48, broad textual disassembly filtered by memory operand and likely store.
text=next(s for s in p.sections if s.name=='.text');hits=[];seen=set();pos=text.raw_ptr
while True:
 pos=p.data.find(bytes.fromhex('480a0000'),pos+1)
 if pos<0 or pos>=text.raw_ptr+text.raw_size:break
 at=text.virtual_address+pos-text.raw_ptr;start,end=fn(at)
 if not 0xe00000<=start<0xfd0000 or start in seen:continue
 seen.add(start)
 for i in cs.disasm(p.read_rva(start,end-start),start):
  if '0xa48]' in i.op_str:hits.append({'at':hex(i.address),'fn':hex(start),'asm':f'{i.mnemonic} {i.op_str}'})
out['idler_a48_refs']=hits
(R/'research/t201_deep_getters.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
