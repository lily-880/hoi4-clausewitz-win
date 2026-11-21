# Read actual initialized native token strings, no getter invocation.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
H=lambda b:hashlib.sha256(b).hexdigest();s=json.loads((Q/'t232_initial_session_rebind.json').read_text());rt=Runtime()
try:
 g=rt.guard();assert g==s['before'];assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
 for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==s['native_controls'][hex(va)]
 for name,h in s['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
 cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True;raw=rt.code(0x253ecd0,2048);flow=walk_flow(cs,raw,0x253ecd0)
 required=('253ed5f shl rbx, 5','253ed63 add rbx, qword ptr [rip + 0x1150836]','253ecd9 cmp byte ptr [rip + 0x1150890], 0','253ece7 cmp ebx, dword ptr [rip + 0x1150887]')
 assert all(x in flow['asm'] for x in required) and not flow['unresolved_edges']
 ptr_rva=0x253ed63+7+0x1150836;init_rva=0x253ecd9+7+0x1150890;count_rva=0x253ece7+6+0x1150887
 r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV';assert r.exact(rt.base+init_rva,1)==b'\x01'
 count=r.i(rt.base+count_rva);assert 19369<count<100000;table=r.q(rt.base+ptr_rva);names={}
 for token,name in [(19364,'alert_level'),(19365,'low'),(19366,'medium'),(19367,'high'),(19369,'alert_margin')]:
  got=r.string(table+token*32);assert got==name;names[str(token)]=got
 stable=r.stable();after=rt.guard();assert after==g
 flow.update(raw_hex=raw.hex(),sha256=H(raw))
 out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'getter_flow':flow,'token_table_pointer_global_rva':hex(ptr_rva),'token_table_init_global_rva':hex(init_rva),'token_table_count_global_rva':hex(count_rva),'token_count':count,'names':names,'stable_dependencies':stable,'raw_dependencies':[{'address':hex(a),'size':n,'hex':b.hex()} for (a,n),b in sorted(r.samples.items())],'scope':'Current initialized token table read through exact native getter arithmetic; never invoked. Does not convert occupation-modifier enum into generic crisis severity.'}
 (Q/'t232_live_token_names.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('raw_dependencies','getter_flow','before','after')},indent=2))
finally:rt.close()
