# Whitelisted full trigger interfaces only; reject short CTriggerEntry factory tables.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest();prev=json.loads((Q/'t228_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
rt=Runtime()
try:
 g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
 assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
 pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz);ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
 def capture(va):
  mm=[x for x in ranges if x[0]<=va<x[1]]
  if mm:assert mm[0][0]==va;size=mm[0][1]-va
  else:size=0x200
  assert size<=0x8000;raw=rt.code(va,size);f=walk_flow(cs,raw,va);f.update(raw_hex=raw.hex(),sha256=H(raw),unwind_bound=bool(mm));return f
 old=json.loads((Q/'t229_winner_semantics_and_ally_pivot.json').read_text(encoding='utf-8'));rows=[];functions={};literals=[]
 full={'.?AVCHasWarTogetherTrigger@@','.?AVCAnyAlliedCountryTrigger@@','.?AVCAllAlliedCountryTrigger@@'}
 for row in old['ally_vtable_scan']['matches']:
  if row['class_name'] not in full:continue
  vt=int(row['vtable_rva'],16);col=struct.unpack('<Q',rt.code(vt-8,8))[0]-rt.base;head=struct.unpack('<6I',rt.code(col,24));assert head[0]==1 and head[5]==col
  name=rt.code(head[3]+0x10,160).split(b'\0')[0].decode();assert name==row['class_name'];slots={}
  for slot in ((0xa8,0xb0) if name=='.?AVCHasWarTogetherTrigger@@' else (0xa8,0xb0,0xc0)):  # C0 is proved only by the two allied-scope evaluators
   target=struct.unpack('<Q',rt.code(vt+slot,8))[0]-rt.base;assert 0<=target<rt.pr.image_size;slots[hex(slot)]=hex(target)
   if hex(target) not in functions:functions[hex(target)]=capture(target)
  rows.append({'class_name':name,'vtable_rva':hex(vt),'slots':slots})
 functions['0xd86fe0']=capture(0xd86fe0)
 for a,f in functions.items():
  reachable={int(line.split(' ',1)[0],16) for line in f['asm']}
  for ins in cs.disasm(bytes.fromhex(f['raw_hex']),int(a,16)):
   if ins.address not in reachable:continue  # bounded window tail is not this function's reachable body
   if ins.mnemonic!='lea' or len(ins.operands)<2:continue
   o=ins.operands[1]
   if o.type!=X86_OP_MEM or o.mem.base!=X86_REG_RIP:continue
   va=ins.address+ins.size+o.mem.disp
   if not 0<=va<rt.pr.image_size-96:continue
   b=rt.code(va,96).split(b'\0')[0]
   if 3<=len(b)<96 and all(32<=x<127 for x in b):literals.append({'function':a,'site':hex(ins.address),'rva':hex(va),'text':b.decode()})
 stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'full_trigger_bindings':rows,'functions':functions,'named_literals':literals,'rejected_factory_rows':[x['class_name'] for x in old['ally_vtable_scan']['matches'] if x['class_name'] not in full],'live_faction_resampling':0,'new_friendly_samples':0,'stable_dependencies':stable,'scope':'New static named common-war/allied-scope pivot only; no faction NULL rechecks or nonwar->friendly inference; no friendly enum promotion from class names.'}
 (Q/'t229_named_pivot_closure.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='functions'},ensure_ascii=False,indent=2));print('functions',{a:{k:f[k] for k in ('reachable_instruction_count','unresolved_edges','external_tails')} for a,f in functions.items()})
finally:rt.close()
