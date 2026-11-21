# Read-only correction: player theatre+0x50 is own-front list; later offsets are neighboring CTheatre+0x50.
# Also CFront loader tag offsets and simple vtable leaves. No game mutation.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP,X86_REG_RCX
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t229_final_seal.json').read_text(encoding='utf-8'))
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
    return out,raw,H(raw)

rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    # Loader 0xf7be60 and section-sanity 0xf775e0
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    functions={}
    loader_lits={}
    for start in (0xf7be60,0xf775e0):
        pr=pdata_of(ranges,start);assert pr and pr[0]==start
        size=pr[1]-pr[0];assert size<=0x8000
        L,raw,sha=lits(rt,start,size)
        cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
        f=walk_flow(cs,raw,start)
        functions[hex(start)]={'scope':'direct-control reachability in bounded byte window; calls opaque; no global-write absence claim','window_start':hex(start),'window_size':size,'reachable_instruction_count':f.get('reachable_instruction_count'),'unresolved_edges':f.get('unresolved_edges'),'external_tails':f.get('external_tails'),'calls':f.get('calls'),'sha256':sha}
        loader_lits[hex(start)]=L
        # compact rcx-relative accesses
        acc=[]
        for ins in cs.disasm(raw,start):
            for op in ins.operands:
                if op.type==X86_OP_MEM and op.mem.base==X86_REG_RCX and op.mem.index==0:
                    acc.append({'site':hex(ins.address),'mnem':ins.mnemonic,'disp':op.mem.disp,'asm':f'{ins.address:x} {ins.mnemonic} {ins.op_str}'})
        functions[hex(start)]['rcx_disps']=acc
    # CFront vtable leaves
    slots=struct.unpack('<'+'Q'*48,rt.code(0x29f23b0,384))
    cs2=Cs(CS_ARCH_X86,CS_MODE_64)
    leaves=[]
    for i,addr in enumerate(slots):
        if not (rt.base<=addr<rt.base+rt.pr.image_size):continue
        rva=addr-rt.base;raw=rt.code(rva,32)
        ins=list(cs2.disasm(raw,rva))
        text=[f'{x.address:x} {x.mnemonic} {x.op_str}' for x in ins[:6]]
        if ins and ins[-1].mnemonic=='ret' or (len(ins)>=2 and ins[1].mnemonic=='ret') or (ins and ins[0].mnemonic in ('mov','movzx','movsx','movsxd') and any(x.mnemonic=='ret' for x in ins[:4])):
            if any(x.mnemonic=='ret' for x in ins[:4]) and all(x.mnemonic in ('mov','movzx','movsx','movsxd','ret') for x in ins[:4]):
                leaves.append({'slot':i,'rva':hex(rva),'asm':text[:4]})
    # Cheap next-target literal presence only, not a full investigation.
    rva,rsz=rt.sections['.rdata'];rdata=rt.code(rva,rsz)
    next_needles=(b'FRONT_INVALID',b'INVALIDATED_FRONT',b'FRONT_INVALIDATED',b'INVALIDATE_FRONT',b'CANNOT_HOLD',b'FRONT_CANNOT',b'HOLD_FRONT',b'FRONT_BROKEN',b'BROKEN_FRONT',b'FRONT_COLLAPSE',b'FRONT_BROKE')
    next_hits=[]
    for n in next_needles:
        off=0
        while len(next_hits)<30:
            i=rdata.find(n,off)
            if i<0:break
            s=i
            while s>0 and 32<=rdata[s-1]<127:s-=1
            t=i
            while t<len(rdata) and 32<=rdata[t]<127:t+=1
            next_hits.append({'needle':n.decode(),'rva':hex(rva+s),'text':rdata[s:t].decode('ascii','replace')})
            off=i+1
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre');assert len(r.array(rt.country+0x168,64))==1
    neighbors=[]
    for k in range(5):
        addr=tp+k*0x1e0
        try:c=rt.cls(addr)
        except Exception as e:
            neighbors.append({'index':k,'addr':hex(addr),'class':'unreadable:'+type(e).__name__});continue
        row={'index':k,'addr':hex(addr),'class':c}
        if 'CTheatre' in c:
            fronts=r.array(addr+0x50,4096) if k==0 or True else []
            # identify owner pointers in theatre header
            hdr=r.exact(addr,0x50)
            owner=[]
            for o in range(0,0x50,8):
                q=struct.unpack_from('<Q',hdr,o)[0]
                if q==rt.country:owner.append({'offset':hex(o),'kind':'player_country'})
                elif q==tp:owner.append({'offset':hex(o),'kind':'player_theatre'})
                else:
                    try:
                        cc=rt.cls(q)
                    except Exception:
                        continue
                    if 'Country' in cc or 'Theatre' in cc:
                        owner.append({'offset':hex(o),'ptr':hex(q),'class':cc})
            backrefs=[]
            own=0
            for p in fronts:
                r.q(p);assert rt.cls(p)=='.?AVCFront@@'
                back=r.q(p+0x18)
                ident=struct.unpack('<I',r.exact(p+0xc,4))[0]
                kind=struct.unpack('<I',r.exact(p+0x8,4))[0]
                if back==addr:own+=1
                backrefs.append({'front':hex(p),'id':ident,'kind':kind,'theatre_back':hex(back),'back_is_this_theatre':back==addr})
            row.update({'front_count':len(fronts),'fronts_backpointing_here':own,'owner_header_hits':owner,'fronts':backrefs})
        neighbors.append(row)
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'functions':functions,'loader_literals':loader_lits,'cfront_leaves':leaves,'next_target_literal_hits':next_hits,'player_theatre':hex(tp),'player_country_theatre_array_count':1,'neighboring_theatres':neighbors,'correction':'Offsets 0x230/0x410/0x5f0/0x7d0 on the first CTheatre object overlap neighboring packed CTheatre+0x50 lists (stride 0x1e0) and are not additional lists of the player theatre. Only player CTheatre+0x50 fronts whose +0x18 back-pointer equals that theatre are current own-theatre membership.','scope':'Membership correction, CFront loader tag evidence, and leaf getters only. REQ_DIVS remains a garrison-order UI label, not missing_divisions. Desired force remains rejected as a substitute. No game mutation.','stable_dependencies':stable}
    (Q/'t230_own_front_correction_and_serializer.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'at_est':out['at_est'],'loader_literals':loader_lits,'rcx_disps_f7be60':functions['0xf7be60']['rcx_disps'][:40],'unresolved':{k:functions[k]['unresolved_edges'] for k in functions},'leaves':leaves,'next_target_literal_hits':next_hits,'neighbors':[{k:v for k,v in n.items() if k!='fronts'}|{'front_ids':[f['id'] for f in n.get('fronts',[])]} for n in neighbors],'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:
    rt.close()
