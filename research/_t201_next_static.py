from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
import re
cs.detail=False
text=next(s for s in p.sections if s.name=='.text')
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
out={};labels=[]
for m in re.finditer(rb'(?<![A-Z0-9_])[A-Z][A-Z0-9_]{6,110}\x00',p.data):
 s=m.group()[:-1].decode('ascii')
 if any(t in s for t in('ISOLAT','ENCIRCL','SUPPLY_CONNECTION','SUPPLY_CONNECT','NO_SUPPLY_LINE')):labels.append({'rva':hex(rv(m.start())),'label':s})
out['isolation_keys']=labels
# Real GS reference is a provenance requirement, not mere offset coincidence.
hits=[];pos=text.raw_ptr;seen=set()
while True:
 pos=p.data.find(struct.pack('<I',0x268),pos+1)
 if pos<0 or pos>=text.raw_ptr+text.raw_size:break
 at=text.virtual_address+pos-text.raw_ptr;st,en=fn(at)
 if st in seen:continue
 seen.add(st);ls=list(cs.disasm(p.read_rva(st,en-st),st));arr=[i for i in ls if '0x268]'in i.op_str and i.mnemonic not in('call','jmp')];gs=[]
 if not arr:continue
 for i in ls:
  m=re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]',i.op_str)
  if m and i.address+i.size+(1 if m[1]=='+'else -1)*int(m[2],16)==0x33dd6b0:gs.append(i)
 if not gs:continue
 def ctxt(i,b=40,a=65):return[f'{j.address:x} {j.mnemonic} {j.op_str}'for j in ls if i.address-b<=j.address<=i.address+a]
 calls=[i for i in ls if any(s in i.op_str for s in('+ 0x78]','+ 0x80]'))]
 hits.append({'fn':hex(st),'GS_refs':[ctxt(i)for i in gs],'array_refs':[ctxt(i)for i in arr],'virtual_slots':[ctxt(i)for i in calls]})
out['GS_bound_combat_array_functions']=hits
ls=clip(0xfd2dc0);out['plan_r15_origin']={'prologue':ls[:55],'r15_assignments':[s for s in ls if any(t in s for t in('mov r15,','xor r15d','lea r15,'))and int(s.split()[0],16)<0xfd4770],'mapping_block':[s for s in ls if 0xfd4620<=int(s.split()[0],16)<=0xfd47c0]}
# Neighboring CArmy supply virtuals may expose connection predicate, not generic scanning.
out['supply_neighbor_vmethods']={}
for slot in range(0x138,0x198,8):
 a=struct.unpack('<Q',p.read_rva(0x29d6d98+slot,8))[0]-0x140000000;ins=[]
 for i in cs.disasm(p.read_rva(a,160),a):
  if i.mnemonic=='int3':break
  ins.append(f'{i.address:x} {i.mnemonic} {i.op_str}')
 out['supply_neighbor_vmethods'][hex(slot)]={'rva':hex(a),'begin':ins[:20]}
(R/'research/t201_next_static.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('ISOLATION_KEYS',json.dumps(labels));print('REAL_GS_ARRAY_FUNCTIONS',[x['fn']for x in hits]);print('PLAN_ORIGIN',json.dumps(out['plan_r15_origin'],indent=2));print('SUPPLY_NEIGHBORS',json.dumps(out['supply_neighbor_vmethods'],indent=2))
