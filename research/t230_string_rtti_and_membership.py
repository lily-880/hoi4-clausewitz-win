# Read-only complete string/RTTI harvest and tight own-front membership. No game writes/calls/save/UI/time.
import sys,json,struct,hashlib,datetime,re
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
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
def asciis(blob,base,pred,limit=400):
    out=[];i=0;n=len(blob)
    while i<n and len(out)<limit:
        if not (32<=blob[i]<127):
            i+=1;continue
        j=i
        while j<n and 32<=blob[j]<127:j+=1
        if j-i>=6 and (i==0 or blob[i-1]==0) and (j==n or blob[j]==0):
            s=blob[i:j].decode('ascii')
            if pred(s):out.append({'rva':hex(base+i),'text':s})
        i=j+1
    return out
INTEREST=re.compile(r'(MISSING|NEEDED|REQUIRED|WANTED|DESIRED|SHORTAGE|STAFF|ASSIGNED|UNASSIGNED|CANNOT_HOLD|HOLD_FRONT|FRONTAGE|FRONT_UNIT|UNIT_REQUEST|DIVISIONS_REQUIRED|DIVISIONS_NEEDED|NR_DIVISIONS|NUM_DIVISIONS|FRONTLINE|FRONT_ORDER|FRONT_CONTROL|FRONT_ARMOR|GARRISON)',re.I)
NARROW=re.compile(r'((MISS\w{0,12}DIV)|(DIV\w{0,16}MISS)|(NEED\w{0,12}DIV)|(DIV\w{0,16}NEED)|(REQ\w{0,12}DIV)|(DIV\w{0,16}REQ)|(WANT\w{0,12}DIV)|(DESIR\w{0,12}DIV)|(FRONT\w{0,20}(NEED|MISS|STAFF|HOLD|SHORT|REQUEST|STRENGTH|UNIT|DIV))|(SHORTAGE)|(STAFFING)|(CANNOT_HOLD)|(FRONTAGE_FULL)|(MISSING_DIV)|(NEEDED_DIV)|(REQUIRED_DIV)|(WANTED_DIV)|(DESIRED_NR)|(NUM_WANTED)|(SUBTRACT_FRONTS))',re.I)
CLASSKEEP=re.compile(r'Front|Staff|Shortage|Garrison|UnitRequest|OrdersGroup|Theatre|Theater|BattlePlan|OrderInstance',re.I)
rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    sections={n: {'va':hex(va),'size':sz} for n,(va,sz) in rt.sections.items()}
    rtti_samples=[];rtti_hits=[];class_counts={};exact_class_hits=[]
    wanted_exact=(b'.?AVCFront@@',b'.?AVCFrontSection@@',b'.?AVCFrontEndIdler@@',b'.?AVCTheatre@@',b'.?AVCTheaterGroup@@')
    for name,(va,sz) in rt.sections.items():
        if sz<=0 or sz>128*1024*1024:continue
        blob=rt.code(va,sz)
        class_counts[name]=blob.count(b'.?AV')
        for needle in wanted_exact+ (b'.?AVCFront',b'.?AUCFront',b'CFrontSection',b'.?AVCAiFront',b'.?AVCFrontLine',b'.?AVCStrategicFront',b'.?AVCBattlePlan'):
            off=0;found=0
            while found<8:
                i=blob.find(needle,off)
                if i<0:break
                # emit surrounding cstring if any
                s=i
                while s>0 and 32<=blob[s-1]<127:s-=1
                t=i
                while t<len(blob) and 32<=blob[t]<127:t+=1
                exact_class_hits.append({'section':name,'rva':hex(va+s),'needle':needle.decode('latin1'),'text':blob[s:t].decode('latin1')})
                off=i+1;found+=1
        if name in ('.rdata','.data','.text') or class_counts[name]:
            off=0
            while len(rtti_hits)<120:
                i=blob.find(b'.?AV',off)
                if i<0:break
                t=i
                while t<len(blob) and 32<=blob[t]<127:t+=1
                s=blob[i:t].decode('ascii','replace')
                if len(rtti_samples)<12 and name=='.rdata':rtti_samples.append({'rva':hex(va+i),'text':s})
                if CLASSKEEP.search(s):
                    rtti_hits.append({'section':name,'rva':hex(va+i),'name':s})
                off=i+4
    # rdata semantic strings
    rva,rsz=rt.sections['.rdata'];rdata=rt.code(rva,rsz)
    strings=asciis(rdata,rva,lambda s:bool(NARROW.search(s)),limit=300)
    # xrefs for a tight subset: exact or strongly named keys, not every modifier
    keep_for_xref=[]
    for row in strings:
        t=row['text']
        if NARROW.search(t) and not t.startswith('N') or t.startswith('TRIGGER_') or t.startswith('ALERT_') or t.startswith('MODIFIER_') is False:
            if any(k in t.upper() for k in ('MISSING','NEEDED','REQUIRED_DIV','WANTED','DESIRED_NR','FRONT_UNIT_REQUEST','SUBTRACT_FRONTS','FRONTAGE','CANNOT_HOLD','STAFF','SHORTAGE','UNASSIGNED_DIV','DIVISIONS_REQUIRED','FRONT_UNITS','FRONT_REQUEST','HOLD')):
                keep_for_xref.append(int(row['rva'],16))
    tva,tsz=rt.sections['.text'];text=rt.code(tva,tsz)
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    wanted=set(keep_for_xref)
    xmap={t:[] for t in wanted}
    for pref in LEA_PREFIXES:
        inst=len(pref)+4;start=0
        while True:
            i=text.find(pref,start)
            if i<0:break
            if i+inst<=len(text):
                disp=struct.unpack_from('<i',text,i+len(pref))[0];tgt=tva+i+inst+disp
                if tgt in xmap and len(xmap[tgt])<16:xmap[tgt].append(tva+i)
            start=i+1
    named=[]
    for row in strings:
        ev=int(row['rva'],16)
        if ev not in xmap:continue
        sites=xmap[ev]
        funcs=[]
        for site in sites:
            pr=pdata_of(ranges,site)
            funcs.append({'site':hex(site),'pdata':[hex(x) for x in pr] if pr else None,'window':(pr[1]-pr[0]) if pr else None})
        named.append({**row,'xrefs':[hex(s) for s in sites],'functions':funcs})
    # Membership: identify the one nonempty +0x98 object on the empty army group; do not resample the two null plan slots.
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    theatres=r.array(rt.country+0x168,64);assert len(theatres)==1
    tp=theatres[0];r.require(tp,'CTheatre')
    def class_hits(addr,size,owner):
        window=r.exact(addr,size);hits=[]
        for off in range(0,size,8):
            p=struct.unpack_from('<Q',window,off)[0]
            if p<0x10000:continue
            try:c=rt.cls(p)
            except Exception:continue
            if CLASSKEEP.search(c):
                hits.append({'owner':owner,'offset':hex(off),'ptr':hex(p),'class':c})
        return hits
    theatre_hits=class_hits(tp,0x400,'theatre')
    groups=r.array(tp+0xc8,128)
    group_hits=[];plan_identities=[]
    for tg in groups:
        r.q(tg);gc=rt.cls(tg)
        group_hits.extend(class_hits(tg,0x200,'theater_group:'+gc))
        for og in r.array(tg+0x48,128):
            r.q(og);oc=rt.cls(og)
            group_hits.extend(class_hits(og,0x180,'orders:'+oc))
            slot=r.q(og+0x98)
            identity={'orders':hex(og),'orders_class':oc,'slot98':hex(slot),'slot98_class':None}
            if slot:
                try:identity['slot98_class']=rt.cls(slot)
                except Exception as e:identity['slot98_class']='unreadable:'+type(e).__name__
            plan_identities.append(identity)
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'sections':sections,'rtti_count_by_section':class_counts,'rtti_samples_rdata':rtti_samples,'rtti_hits':rtti_hits,'exact_class_hits':exact_class_hits,'narrow_strings':strings,'named_consumers':named,'theatre_extended_hits':theatre_hits,'group_extended_hits':group_hits,'plan_slot_identities':plan_identities,'scope':'String/RTTI harvest plus tight class membership on the current single theatre. The two COrdersGroup+0x98 null plan slots are recorded as absent, not resampled. Army-group+0x98 is identified by class only. Desired/wanted/volunteer/frontage names are not schema missing_divisions. No heap-wide front walk, no game mutation.','stable_dependencies':stable}
    (Q/'t230_string_rtti_and_membership.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'at_est':out['at_est'],'rtti_count_by_section':class_counts,'rtti_samples':rtti_samples[:8],'rtti_hit_count':len(rtti_hits),'rtti_names':[x['name'] for x in rtti_hits][:40],'exact_class_hits':exact_class_hits,'narrow_string_count':len(strings),'narrow_texts':[s['text'] for s in strings],'named_count':len(named),'named':[{'text':n['text'],'xrefs':n['xrefs'],'pdata':[f['pdata'] for f in n['functions']]} for n in named if n['xrefs']],'theatre_hits':theatre_hits,'group_hits':group_hits,'plan_slot_identities':plan_identities,'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:
    rt.close()
