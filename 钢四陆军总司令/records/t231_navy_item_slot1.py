# Read-only: second CNavyTheaterGroupItem slot literals, to confirm or reject the 2-slot vtable.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t230_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    slot1=0x1eafb08
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    lo,hi=0,len(ranges);pr=None
    while lo<hi:
        mid=(lo+hi)//2;s,e,_=ranges[mid]
        if slot1<s:hi=mid
        elif slot1>=e:lo=mid+1
        else:pr=ranges[mid];break
    if not (pr and pr[0]<=slot1<pr[1] and pr[1]-pr[0]<=0x4000):
        start,end=slot1,slot1+512;f={'reachable_instruction_count':None,'unresolved_edges':['no_pdata_or_oversize'],'external_tails':[]}
        raw=rt.code(start,512);cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
        pdata_status={'pdata':None,'bounded_unwound':False}
    else:
        start,end=pr[0],pr[1];raw=rt.code(start,end-start);cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
        f=walk_flow(cs,raw,start);pdata_status={'pdata':[hex(x) for x in pr],'bounded_unwound':True}
    lits=[]
    rva,rsz=rt.sections['.rdata']
    for ins in cs.disasm(raw,start):
        if ins.mnemonic!='lea' or len(ins.operands)<2:continue
        op=ins.operands[1]
        if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_RIP:continue
        target=ins.address+ins.size+op.mem.disp
        if not rva<=target<rva+rsz:continue
        b=rt.code(target,160).split(b'\0')[0]
        if 3<=len(b)<=159 and all(32<=x<127 or x in (9,10,13) for x in b):
            lits.append({'site':hex(ins.address),'target':hex(target),'text':b.decode('ascii','replace')})
    after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'slot1':hex(slot1),'pdata':pdata_status['pdata'],'bounded_unwound':pdata_status['bounded_unwound'],'window_start':hex(start),'window_size':end-start,'sha256':H(raw),'reachable_instruction_count':f.get('reachable_instruction_count'),'unresolved_edges':f.get('unresolved_edges'),'external_tails':f.get('external_tails'),'literals':lits,'scope':'Second slot of the two-pointer table after the CNavyTheaterGroupItem COL. Not invoked. Even if the class is accepted, this is not a land-crisis severity consumer.'}
    (Q/'t231_navy_item_slot1.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in out if k not in ('before','after')},ensure_ascii=False,indent=2))
finally:
    rt.close()
