# Read-only: resolve CFront/CAIFront vtables, named desired/REQ_DIVS consumers, and current own-front roots.
# No game writes/calls/save/UI/time changes. Desired force is never treated as missing_divisions.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from _t205_flow import walk_flow
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t229_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
LEA_PREFIXES=(b'\x48\x8d\x05',b'\x48\x8d\x0d',b'\x48\x8d\x15',b'\x48\x8d\x1d',b'\x48\x8d\x35',b'\x48\x8d\x3d',
              b'\x4c\x8d\x05',b'\x4c\x8d\x0d',b'\x4c\x8d\x15',b'\x4c\x8d\x1d',b'\x4c\x8d\x35',b'\x4c\x8d\x3d')
def pdata_of(ranges,rva):
    lo,hi=0,len(ranges)
    while lo<hi:
        mid=(lo+hi)//2;s,e,_=ranges[mid]
        if rva<s:hi=mid
        elif rva>=e:lo=mid+1
        else:return ranges[mid]
    return None
def collect_xrefs(text,tva,targets):
    hits={t:[] for t in targets}
    for pref in LEA_PREFIXES:
        inst=len(pref)+4;start=0
        while True:
            i=text.find(pref,start)
            if i<0:break
            if i+inst<=len(text):
                disp=struct.unpack_from('<i',text,i+len(pref))[0];tgt=tva+i+inst+disp
                if tgt in hits and len(hits[tgt])<24:hits[tgt].append(tva+i)
            start=i+1
    return hits
def find_va_refs(sections,value,limit=32):
    raw=struct.pack('<Q',value);out=[]
    for name,(va,sz) in sections:
        if sz<=0 or sz>128*1024*1024:continue
        blob=rt.code(va,sz);off=0
        while len(out)<limit:
            i=blob.find(raw,off)
            if i<0:break
            if i%8==0:out.append({'section':name,'rva':hex(va+i)})
            off=i+1
    return out
def find_rva32(sections,rva,limit=32):
    raw=struct.pack('<I',rva);out=[]
    for name,(va,sz) in sections:
        if name not in ('.rdata','.data'):continue
        blob=rt.code(va,sz);off=0
        while len(out)<limit:
            i=blob.find(raw,off)
            if i<0:break
            if i%4==0:out.append({'section':name,'rva':hex(va+i)})
            off=i+4
    return out
rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    sections=list(rt.sections.items());secmap=dict(sections)
    # Exact short class names in .data
    dva,dsz=rt.sections['.data'];data=rt.code(dva,dsz)
    classes=[]
    for needle in (b'.?AVCFront@@',b'.?AVCFrontSection@@',b'.?AVCAIFront@@',b'.?AUSPerCountrySection@CFrontSection@@',
                   b'.?AVCTheatre@@',b'.?AVCTheaterGroup@@',b'.?AVCTheatreManager',b'.?AVCFrontageFullTrigger@@',
                   b'.?AVCFrontControlStrategyData@@',b'.?AUSInterpolatedFrontBundle',b'.?AVNTheatreManager'):
        i=data.find(needle)
        if i>=0:
            s=i
            while s>0 and 32<=data[s-1]<127:s-=1
            t=i
            while t<len(data) and 32<=data[t]<127:t+=1
            classes.append({'name':data[s:t].decode(),'name_rva':hex(dva+s),'td_rva':hex(dva+s-0x10)})
    # Also harvest short (len<80) data names containing exact tokens
    extra=[];off=0
    while len(extra)<80:
        i=data.find(b'.?AV',off)
        if i<0:break
        t=i
        while t<len(data) and 32<=data[t]<127:t+=1
        name=data[i:t].decode('ascii','replace')
        if len(name)<80 and any(k in name for k in ('CFront@@','CAIFront','CFrontSection','TheatreManager','CTheatreManager','CFrontLine','CStrategicFront')) and 'lambda' not in name and 'reference_wrapper' not in name:
            extra.append({'name':name,'name_rva':hex(dva+i),'td_rva':hex(dva+i-0x10)})
        off=i+4
    # Resolve vtables using live CTheatre as method control, then apply to CFront family.
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre')
    vt=r.q(tp);col=r.q(vt-8)
    sig,off,cd,td=struct.unpack('<IIII',rt.pr.read(col,16))
    theatre_control={'theatre':hex(tp),'vtable_rva':hex(vt-rt.base),'col':hex(col),'col_rva':hex(col-rt.base),'sig':sig,'td_rva':hex(td),'name':rt.pr.read(rt.base+td+0x10,64).split(b'\0')[0].decode()}
    assert theatre_control['name']=='.?AVCTheatre@@' and sig==1
    vtables=[]
    for row in classes+extra:
        tdr=int(row['td_rva'],16)
        cols=[]
        for hit in find_rva32(sections,tdr,limit=16):
            loc=int(hit['rva'],16)
            # COL may start 12 bytes before the td field
            for start in (loc-12,loc):
                if start<=0:continue
                b=rt.code(start,24)
                sig2,o2,cd2,td2=struct.unpack_from('<IIII',b,0)
                if sig2==1 and td2==tdr:
                    cols.append(start);break
        vt_rvas=[]
        for cva in cols:
            for ref in find_va_refs(sections,rt.base+cva,limit=8):
                # vtable usually follows the COL pointer
                vr=int(ref['rva'],16)+8
                vt_rvas.append(hex(vr))
        vtables.append({**row,'col_rvas':[hex(x) for x in cols],'vtable_rvas':vt_rvas})
    # Named strings of interest in rdata+data
    needles=(b'_TotalFrontDesiredNrDivisions',b'TotalFrontDesiredNrDivisions',b'REQ_DIVS',b'ReqDivs',b'Req_Divs',
             b'_TotalFront',b'DesiredNrDivisions',b'MissingDivisions',b'missing_divisions',b'RequiredNrDivisions',
             b'NeededNrDivisions',b'_NormalFrontUnits',b'ForceConcentrationUnits',b'The following equations need some rework',
             b'AI front unit caches',b'BalanceUnitsOnFrontBetweenArmies',b'SpatializedDistributionOfUnassignedUnits')
    found_strings=[]
    for name,(va,sz) in sections:
        if name not in ('.rdata','.data'):continue
        blob=rt.code(va,sz)
        for needle in needles:
            off=0;n=0
            while n<8:
                i=blob.find(needle,off)
                if i<0:break
                s=i
                while s>0 and 32<=blob[s-1]<127:s-=1
                t=i
                while t<len(blob) and 32<=blob[t]<127:t+=1
                found_strings.append({'section':name,'rva':hex(va+s),'text':blob[s:t].decode('ascii','replace'),'needle':needle.decode('latin1')})
                off=i+1;n+=1
    tva,tsz=rt.sections['.text'];text=rt.code(tva,tsz)
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    targets=sorted({int(s['rva'],16) for s in found_strings if s['section']=='.rdata'})
    xmap=collect_xrefs(text,tva,set(targets))
    cs=Cs(CS_ARCH_X86,CS_MODE_64);cs.detail=True
    functions={}
    string_funcs=[]
    for s in found_strings:
        ev=int(s['rva'],16);sites=xmap.get(ev,[])
        funcs=[]
        for site in sites:
            pr=pdata_of(ranges,site)
            if not pr:continue
            start,end,unw=pr;size=end-start
            rec={'site':hex(site),'pdata':[hex(x) for x in pr],'window_size':size}
            key=hex(start)
            if key not in functions and size<=0x4000:
                raw=rt.code(start,size);f=walk_flow(cs,raw,start)
                functions[key]={'scope':'direct-control reachability in bounded byte window; calls opaque; no global-write absence claim','window_start':key,'window_size':size,'reachable_instruction_count':f.get('reachable_instruction_count'),'unresolved_edges':f.get('unresolved_edges'),'external_tails':f.get('external_tails'),'asm':f.get('asm') or f.get('instructions') or None,'sha256':H(raw)}
                # keep a compact instruction list if present
                if 'instructions' in f and 'asm' not in functions[key]:
                    functions[key]['instructions']=f['instructions']
                for k,v in f.items():
                    if k not in functions[key] and k in ('calls','conditional_branches','returns','reachable_sites'):
                        functions[key][k]=v
            funcs.append(rec)
        string_funcs.append({**s,'xrefs':[hex(x) for x in sites],'functions':funcs})
    # Bounded own-front vector search on known objects only (theatre 0x800, theater/orders already inventoried, country 0x200 stride-limited, gs/idler small windows).
    def vectors_of(addr,size,owner):
        hits=[]
        window=r.exact(addr,size)
        for off in range(0,size-15,8):
            data,cap,n=struct.unpack_from('<QII',window,off)
            if not (0<n<=cap<=4096 and data>0x10000):continue
            # only inspect first element class
            try:
                first=struct.unpack('<Q',rt.pr.read(data,8))[0]
                c=rt.cls(first)
            except Exception:
                continue
            if any(k in c for k in ('CFront@@','CFrontSection@@','CAIFront@@')):
                # bind remaining members boundedly
                members=[]
                try:
                    arr=r.array(addr+off,4096)
                except Exception:
                    arr=[]
                for p in arr[:64]:
                    try:members.append({'ptr':hex(p),'class':rt.cls(p)})
                    except Exception as e:members.append({'ptr':hex(p),'class':'unreadable:'+type(e).__name__})
                hits.append({'owner':owner,'offset':hex(off),'count':n,'capacity':cap,'inspected':len(members),'members':members,'first_class':c})
        return hits
    front_vectors=[]
    front_vectors += vectors_of(tp,0x800,'theatre')
    for tg in r.array(tp+0xc8,128):
        front_vectors += vectors_of(tg,0x300,'theater_group')
        for og in r.array(tg+0x48,128):
            front_vectors += vectors_of(og,0x180,'orders')
    # country: scan 0x000-0x2000 in 8-byte steps is a bit wide but still bounded and class-gated
    front_vectors += vectors_of(rt.country,0x2000,'country')
    front_vectors += vectors_of(rt.gs,0xA00,'gamestate')
    front_vectors += vectors_of(rt.idler,0x900,'idler')
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'theatre_rtti_control':theatre_control,'classes':classes,'extra_classes':extra,'vtables':vtables,'named_strings':string_funcs,'functions':functions,'front_vectors':front_vectors,'scope':'CFront/CAIFront vtable resolution and named desired/REQ_DIVS consumers only. _TotalFrontDesiredNrDivisions is independently named desired force, not missing_divisions. No empty-plan resampling, no world heap walk, no game mutation.','stable_dependencies':stable}
    (Q/'t230_named_desired_and_front_roots.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'at_est':out['at_est'],'theatre_rtti_control':theatre_control,'classes':classes,'extra_classes':extra,'vtables':[{k:v for k,v in row.items()} for row in vtables],'strings':[{'text':s['text'],'rva':s['rva'],'xrefs':s['xrefs'],'functions':s['functions']} for s in string_funcs],'function_windows':{k:{kk:vv for kk,vv in f.items() if kk in ('window_start','window_size','reachable_instruction_count','unresolved_edges','external_tails','sha256')} for k,f in functions.items()},'front_vectors':front_vectors,'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:
    rt.close()
