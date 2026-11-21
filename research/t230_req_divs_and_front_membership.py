# Read-only: name REQ_DIVS/desired-function literals, classify current theatre CFront lists, no game mutation.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_MEM,X86_REG_RIP
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t229_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h

def literals(rt,start,size):
    cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
    raw=rt.code(start,size);out=[]
    rva,rsz=rt.sections['.rdata'];dva,dsz=rt.sections['.data']
    for ins in cs.disasm(raw,start):
        if ins.mnemonic!='lea' or len(ins.operands)<2:continue
        op=ins.operands[1]
        if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_RIP:continue
        target=ins.address+ins.size+op.mem.disp
        if rva<=target<rva+rsz or dva<=target<dva+dsz:
            b=rt.code(target,160)
            # c-string if printable
            s=b.split(b'\0')[0]
            text=s.decode('ascii','replace') if 2<=len(s)<=159 and all(32<=x<127 or x in (9,10,13) for x in s) else None
            out.append({'site':hex(ins.address),'target':hex(target),'text':text,'raw16':b[:16].hex()})
    return out,H(raw)

def pdata_of(ranges,rva):
    lo,hi=0,len(ranges)
    while lo<hi:
        mid=(lo+hi)//2;s,e,_=ranges[mid]
        if rva<s:hi=mid
        elif rva>=e:lo=mid+1
        else:return ranges[mid]
    return None

rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    windows=[]
    for start,size,name in ((0x697db0,2326,'total_front_desired_equations'),(0x177d240,5626,'req_divs_ui')):
        lits,sha=literals(rt,start,size)
        windows.append({'name':name,'start':hex(start),'window_size':size,'sha256':sha,'literals':lits})
    # CFront vtable first 40 slots: collect pdata+literals (bounded)
    vtv=0x29f23b0
    slots=struct.unpack('<'+'Q'*40,rt.code(vtv,320))
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    methods=[]
    for i,addr in enumerate(slots):
        if not (rt.base<=addr<rt.base+rt.pr.image_size):
            methods.append({'slot':i,'rva':hex(addr-rt.base) if addr>rt.base else hex(addr),'kind':'non_image'});continue
        rva=addr-rt.base;pr=pdata_of(ranges,rva)
        item={'slot':i,'rva':hex(rva),'pdata':[hex(x) for x in pr] if pr else None}
        if pr and pr[1]-pr[0]<=0x3000:
            lits,sha=literals(rt,pr[0],pr[1]-pr[0]);item.update({'window':pr[1]-pr[0],'sha256':sha,'literals':[x['text'] for x in lits if x['text']]})
        methods.append(item)
    # CAIFront exact name
    dva,dsz=rt.sections['.data'];data=rt.code(dva,dsz)
    caifront=[]
    off=0
    while len(caifront)<20:
        i=data.find(b'CAIFront',off)
        if i<0:break
        s=i
        while s>0 and 32<=data[s-1]<127:s-=1
        t=i
        while t<len(data) and 32<=data[t]<127:t+=1
        name=data[s:t].decode('ascii','replace')
        if len(name)<70 and 'lambda' not in name and 'Func_impl' not in name:
            caifront.append({'name':name,'rva':hex(dva+s)})
        off=i+1
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre')
    offsets=(0x50,0x230,0x410,0x5f0,0x7d0)
    lists={}
    for off in offsets:
        arr=r.array(tp+off,4096)
        rows=[]
        for p in arr:
            r.q(p);c=rt.cls(p);assert c=='.?AVCFront@@'
            hdr=r.exact(p,0x90)
            dwords=list(struct.unpack_from('<'+'I'*8,hdr,0))
            qwords=list(struct.unpack_from('<'+'Q'*8,hdr,0))
            # do not interpret un-named dwords as missing/desired
            rows.append({'ptr':hex(p),'class':c,'u32_0_1c':dwords,'qword_hints':[hex(x) for x in qwords[:6]]})
        lists[hex(off)]={'count':len(arr),'ptrs':[x['ptr'] for x in rows],'rows':rows}
    # set relationships
    sets={k:set(v['ptrs']) for k,v in lists.items()}
    relations={k:{k2: {'intersection':len(sets[k]&sets[k2]),'only_left':len(sets[k]-sets[k2]),'only_right':len(sets[k2]-sets[k])} for k2 in lists if k2!=k} for k in lists}
    # If a front qword looks like a country pointer, classify with class+tag when possible, still no missing calc.
    country_hits=[]
    for off,payload in lists.items():
        for row in payload['rows']:
            p=int(row['ptr'],16)
            window=r.exact(p,0x90)
            found=[]
            for o in range(0,0x90,8):
                q=struct.unpack_from('<Q',window,o)[0]
                if q==rt.country:
                    found.append({'offset':hex(o),'kind':'self_country'})
                    continue
                try:
                    c=rt.cls(q)
                except Exception:
                    continue
                if 'Country' in c:
                    found.append({'offset':hex(o),'ptr':hex(q),'class':c})
            if found:
                country_hits.append({'front':row['ptr'],'list':off,'hits':found})
    # slice of REQ_DIVS around the key
    cs=Cs(CS_ARCH_X86,CS_MODE_64)
    raw=rt.code(0x177ddc0,0x200)
    req_slice=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(raw,0x177ddc0)]
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'windows':windows,'cfront_vtable_rva':'0x29f23b0','cfront_methods':methods,'caifront_short_names':caifront,'theatre':hex(tp),'front_lists':{k:{'count':v['count'],'ptrs':v['ptrs'],'headers':v['rows']} for k,v in lists.items()},'list_relations':relations,'front_country_pointer_hits':country_hits,'req_divs_slice':req_slice,'scope':'Literal naming and current theatre CFront list membership only. Header u32 values are raw, not missing/desired counts. _TotalFrontDesiredNrDivisions remains desired-force. No empty-plan scan, no game mutation.','stable_dependencies':stable}
    (Q/'t230_req_divs_and_front_membership.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'at_est':out['at_est'],'window_literals':{w['name']:{'sha256':w['sha256'],'literals':[x for x in w['literals'] if x['text']]} for w in windows},'caifront_short_names':caifront,'method_literals':[{'slot':m['slot'],'rva':m.get('rva'),'literals':m.get('literals')} for m in methods if m.get('literals')],'front_counts':{k:v['count'] for k,v in lists.items()},'relations':relations,'country_hits_count':len(country_hits),'country_hit_offsets':sorted({h['offset'] for row in country_hits for h in row['hits']}),'sample_headers':{k:v['rows'][:2] for k,v in lists.items()},'req_divs_slice':req_slice,'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:
    rt.close()
