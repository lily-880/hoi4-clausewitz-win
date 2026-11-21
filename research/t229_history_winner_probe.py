# Current loaded history semantics only; no game writes/calls/save/UI/time changes.
import sys,json,struct,hashlib,datetime,re
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
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';roots=r.array(rt.gs+0x880,2048);manager=roots[rt.index];r.q(manager);mc=rt.cls(manager);assert mc=='.?AVCManager@NCombatLog@@'
 groups=r.array(manager+8,128);pool=r.q(rt.base+0x33ea870);pool_cap=r.i(rt.base+0x33ea878);pool_count=r.i(rt.base+0x33ea87c);assert 0<pool_count<=pool_cap<=100000
 rows=[];group_rows=[];seen=set();limit=64
 for gp in groups:
  r.q(gp);gc=rt.cls(gp);assert 'COrdersGroupLogs' in gc;handle=r.q(gp+0xe0)
  ptr,cap,n=struct.unpack('<QII',r.exact(gp+0xc8,16));assert 0<=n<=cap<=100000
  group_rows.append({'group':hex(gp),'class':gc,'handle':hex(handle),'reference_count':n})
  for j in range(n):
   if len(rows)>=limit:break
   raw=r.exact(ptr+j*8,8);idx,flag=struct.unpack_from('<IB',raw);assert idx<pool_count and flag in (0,1)
   rec=pool+idx*0x448;r.q(rec);rc=rt.cls(rec);assert 'SCombatData' in rc
   defensive,snow,overrun,player_attacker=struct.unpack('<4B',r.exact(rec+0x444,4));assert all(x in (0,1) for x in (defensive,snow,overrun,player_attacker))
   rows.append({'group':hex(gp),'group_handle':hex(handle),'ordinal':j,'reference_address':hex(ptr+j*8),'record_index':idx,'record':hex(rec),'record_class':rc,'reference_result_byte':flag,'defensive_victory':defensive,'snow':snow,'overrun':overrun,'player_is_attacker':player_attacker,'province_id':r.i(rec+0x440)})
   seen.add(flag)
   if seen=={0,1}:break
  if seen=={0,1} or len(rows)>=limit:break
 active=[]
 for cp in r.array(rt.gs+0x268,4096):
  uid=r.i(cp+0x1c)
  if uid not in (3072,3096,3097):continue
  r.require(cp,'CLandCombat');active.append({'combat_id':uid,'type':r.i(cp+0x18),'combat':hex(cp),'id_in_history_pool_index_range':0<=uid<pool_count})
 # Find the genuine unwind entry containing the old UI read site, not a guessed neighbor.
 pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz);ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)];matches=[x for x in ranges if x[0]<=0x178f7a6<x[1]];assert len(matches)==1
 start,end,unwind=matches[0];assert end-start<=0x10000
 cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True;raw=rt.code(start,end-start);f=walk_flow(cs,raw,start);f.update(raw_hex=raw.hex(),sha256=H(raw),pdata_entry=[hex(v) for v in matches[0]])
 literals=[];rva,rsz=rt.sections['.rdata']
 for ins in cs.disasm(raw,start):
  if ins.mnemonic!='lea' or len(ins.operands)<2:continue
  op=ins.operands[1]
  if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_RIP:continue
  target=ins.address+ins.size+op.mem.disp
  if not rva<=target<rva+rsz:continue
  b=rt.code(target,96).split(b'\0')[0]
  if 3<=len(b)<=95 and all(32<=x<127 for x in b):literals.append({'site':hex(ins.address),'rva':hex(target),'text':b.decode()})
  if len(literals)>=128:break
 # New bounded named serializer registration clips; never run a serializer/parser.
 tokens=[];cs2=Cs(CS_ARCH_X86,CS_MODE_64)
 mp=json.loads((Q/'t163_script_token_map.json').read_text(encoding='utf-8'))
 for row in mp:
  if row['token'] not in (0x3756,0x4dbc,0x4dbe):continue
  va=int(row['registration_rva'],16);b=rt.code(va,64);tokens.append(dict(row,raw_hex=b.hex(),asm=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs2.disasm(b,va)]))
 stable=r.stable();after=rt.guard();assert after==g
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'manager':hex(manager),'manager_class':mc,'country_manager_count':len(roots),'groups':group_rows,'reference_inspection_limit':limit,'references_inspected':len(rows),'references':rows,'pool':hex(pool),'pool_count':pool_count,'pool_capacity':pool_cap,'active_controls':active,'ui_function':f,'ui_literals':literals,'token_registration_clips':tokens,'stable_dependencies':stable,'raw_dependencies':[{'address':hex(a),'size':n,'hex':b.hex()} for (a,n),b in sorted(r.samples.items())],'scope':'Retained result byte is not presumed side selector or active combat ID; no result export until native ID bridge proved. No date conversion or zero-loss close recapture.'}
 (Q/'t229_history_winner_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('ui_function','raw_dependencies','token_registration_clips')},ensure_ascii=False,indent=2));print('UI',hex(start),hex(end),f['reachable_instruction_count'],f['unresolved_edges'])
finally:rt.close()
