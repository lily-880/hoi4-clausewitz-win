# Read-only: identify the ALERT_PRIORITY function's class and the opaque 0x2284870 leaf.
# No game writes/calls/save/UI/time.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
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

def lits(rt,start,size):
    cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True;raw=rt.code(start,size);out=[]
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

rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    target=rt.base+0x1eeff60
    raw=struct.pack('<Q',target)
    slots=[]
    for name,(va,sz) in rt.sections.items():
        if name not in ('.rdata','.data'):continue
        blob=rt.code(va,sz);off=0
        while len(slots)<16:
            i=blob.find(raw,off)
            if i<0:break
            if i%8==0:
                slots.append({'section':name,'slot_rva':hex(va+i),'vtable_guess':hex(va+i-8) if i>=8 else None})
            off=i+8
    # For each slot, read preceding pointer as possible COL and decode RTTI
    identities=[]
    for s in slots:
        slot=int(s['slot_rva'],16)
        # scan backward up to 64 qwords for a COL-like pointer (signature 1)
        ident={'slot_rva':s['slot_rva'],'section':s['section'],'class':None,'vtable_rva':None,'slot_index':None}
        for back in range(0,64):
            col_ptr_rva=slot-8-back*8
            if col_ptr_rva<=0:break
            col=struct.unpack('<Q',rt.code(col_ptr_rva,8))[0]
            if not (rt.base<=col<rt.base+rt.pr.image_size):continue
            hdr=rt.pr.read(col,24)
            sig,off,cd,td=struct.unpack_from('<IIII',hdr,0)
            if sig==1 and 0<td<rt.pr.image_size:
                name=rt.pr.read(rt.base+td+0x10,160).split(b'\0')[0].decode('ascii','replace')
                ident.update({'class':name,'col_rva':hex(col-rt.base),'td_rva':hex(td),'vtable_rva':hex(col_ptr_rva+8),'slot_index':(slot-(col_ptr_rva+8))//8})
                break
        identities.append(ident)
    # 0x2284870 itself
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    pr=pdata_of(ranges,0x2284870)
    helper=None
    if pr and pr[1]-pr[0]<=0x2000:
        start,end,_=pr;raw=rt.code(start,end-start);cs=Cs(CS_ARCH_X86,CS_MODE_64)
        f=walk_flow(cs,raw,start)
        helper={'window_start':hex(start),'window_size':end-start,'sha256':H(raw),'reachable_instruction_count':f.get('reachable_instruction_count'),'unresolved_edges':f.get('unresolved_edges'),'external_tails':f.get('external_tails'),'calls':f.get('calls'),'asm':[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(raw,start)][:120],'literals':lits(rt,start,end-start),'scope':'direct-control reachability in bounded byte window; calls opaque; not invoked; no global-write absence claim'}
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'vtable_slots':slots,'identities':identities,'helper_2284870':helper,'scope':'Class identity of the ALERT_PRIORITY tooltip/details function and bounded disassembly of its singleton getter. Not invoked. HIGH/NORMAL is not automatically schema severity.','stable_dependencies':stable}
    (Q/'t231_alert_priority_identity.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'at_est':out['at_est'],'identities':identities,'helper':None if not helper else {k:helper[k] for k in ('window_start','window_size','sha256','reachable_instruction_count','unresolved_edges','external_tails','calls','literals')},'helper_asm_head':None if not helper else helper['asm'][:40],'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:
    rt.close()
