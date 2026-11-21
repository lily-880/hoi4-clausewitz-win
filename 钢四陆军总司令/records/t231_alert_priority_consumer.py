# Read-only analysis of the independently named ALERT_PRIORITY consumer 0x1eeff60.
# No game writes/calls/save/UI/time. Do not treat alert 3/4 IDs or thresholds as severity.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP,X86_REG_RCX,X86_REG_RDX,X86_REG_R8,X86_REG_R9
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t230_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h

def pdata_of(ranges,rva):
    lo,hi=0,len(ranges)
    while lo<hi:
        mid=(lo+hi)//2;s,e,_=ranges[mid]
        if rva<s:hi=mid
        elif rva>=e:lo=mid+1
        else:return ranges[mid]
    return None

def literals(rt,start,size):
    cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
    raw=rt.code(start,size);out=[]
    rva,rsz=rt.sections['.rdata']
    for ins in cs.disasm(raw,start):
        if ins.mnemonic!='lea' or len(ins.operands)<2:continue
        op=ins.operands[1]
        if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_RIP:continue
        target=ins.address+ins.size+op.mem.disp
        if not rva<=target<rva+rsz:continue
        b=rt.code(target,160).split(b'\0')[0]
        if 3<=len(b)<=159 and all(32<=x<127 or x in (9,10,13) for x in b):
            out.append({'site':hex(ins.address),'target':hex(target),'text':b.decode('ascii','replace')})
    return out

def accesses(raw,start):
    cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True;rows=[]
    for ins in cs.disasm(raw,start):
        for i,op in enumerate(ins.operands):
            if op.type!=X86_OP_MEM:continue
            rows.append({'site':hex(ins.address),'mnem':ins.mnemonic,'op':i,'base':op.mem.base,'index':op.mem.index,'disp':op.mem.disp,'asm':f'{ins.address:x} {ins.mnemonic} {ins.op_str}'})
    return rows

rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    start,end=0x1eeff60,0x1ef01e0;size=end-start;assert size==640
    raw=rt.code(start,size);cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
    f=walk_flow(cs,raw,start)
    func={'scope':'direct-control reachability in bounded byte window; calls opaque; no global-write absence claim','window_start':hex(start),'window_size':size,'reachable_instruction_count':f.get('reachable_instruction_count'),'unresolved_edges':f.get('unresolved_edges'),'external_tails':f.get('external_tails'),'calls':f.get('calls'),'sha256':H(raw),'asm':[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(raw,start)]}
    lits=literals(rt,start,size)
    acc=accesses(raw,start)
    # Callers of 0x1eeff60: E8 rel32
    tva,tsz=rt.sections['.text'];text=rt.code(tva,tsz)
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    callers=[];off=0
    while len(callers)<24:
        i=text.find(b'\xe8',off)
        if i<0:break
        if i+5<=len(text):
            rel=struct.unpack_from('<i',text,i+1)[0]
            if tva+i+5+rel==start:
                site=tva+i;pr=pdata_of(ranges,site)
                rec={'site':hex(site),'pdata':[hex(x) for x in pr] if pr else None,'window':(pr[1]-pr[0]) if pr else None}
                if pr and pr[1]-pr[0]<=0x3000:
                    rec['literals']=literals(rt,pr[0],pr[1]-pr[0])
                    rec['sha256']=H(rt.code(pr[0],pr[1]-pr[0]))
                    rec['unresolved']=walk_flow(Cs(CS_ARCH_X86,CS_MODE_64),rt.code(pr[0],pr[1]-pr[0]),pr[0]).get('unresolved_edges')
                callers.append(rec)
        off=i+1
    # Callers of the huge token-table alert_level site are registration, recorded only as such.
    alert_level={'rva':'0x2b36ae8','text':'alert_level','site':'0x1052a9','pdata':['0x83760','0x119491','0x309285c'],'scope':'script-token registration table, not accepted as a crisis-severity consumer'}
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    # No new unit/alert-text scan. Optional: if the consumer clearly reads a global/setting, bind that setting only.
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'function':func,'literals':lits,'accesses':acc,'callers':callers,'alert_level_token':alert_level,'scope':'Independently named ALERT_PRIORITY* consumer and its callers only. Not invoked. HIGH/NORMAL names are not automatically schema severity. Registration parameter 5 / alert 3/4 IDs / supply thresholds are not used as severity. No census or notes expansion.','stable_dependencies':stable}
    (Q/'t231_alert_priority_consumer.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'at_est':out['at_est'],'window':{'start':hex(start),'size':size,'sha256':func['sha256'],'reachable':func['reachable_instruction_count'],'unresolved':func['unresolved_edges'],'tails':func['external_tails'],'calls':func['calls']},'literals':lits,'asm':func['asm'],'interesting_accesses':[a for a in acc if a['disp'] in (0x448,0x410,0x438,5,1,0) or a['mnem'] in ('cmp','test','movzx','lea')],'callers':[{k:v for k,v in c.items() if k!='literals'}|{ 'literal_texts':[x['text'] for x in c.get('literals') or []]} for c in callers],'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:
    rt.close()
