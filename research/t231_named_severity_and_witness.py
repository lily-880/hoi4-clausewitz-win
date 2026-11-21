# Read-only: named severity-literal harvest + already-qualified crisis witness field bind.
# No game writes/calls/save/UI/time. Do not expand 3/25 census, notes, or feed.
import sys,json,struct,hashlib,datetime,re
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
from t227_qualified_crisis_replay import supply
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t230_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
LEA_PREFIXES=(b'\x48\x8d\x05',b'\x48\x8d\x0d',b'\x48\x8d\x15',b'\x48\x8d\x1d',b'\x48\x8d\x35',b'\x48\x8d\x3d',
              b'\x4c\x8d\x05',b'\x4c\x8d\x0d',b'\x4c\x8d\x15',b'\x4c\x8d\x1d',b'\x4c\x8d\x35',b'\x4c\x8d\x3d')
NARROW=re.compile(r'(SEVERITY|SEVERE(?!D)|ALERT_LEVEL|ALERT_PRIORITY|CRISIS_SEV|PRIORITY_LEVEL|CRITICAL_ALERT|ALERT_CRITICAL|WARNING_LEVEL|IMPORTANCE|URGENCY|ALERT_COLOR|ALERT_COLOUR|ALERT_ICON|ICON_FRAME|ALERT_CATEGORY|ALERT_TYPE)',re.I)
# Note: SEVERED excluded; Chinese title wording is not an independent native name.

def pdata_of(ranges,rva):
    lo,hi=0,len(ranges)
    while lo<hi:
        mid=(lo+hi)//2;s,e,_=ranges[mid]
        if rva<s:hi=mid
        elif rva>=e:lo=mid+1
        else:return ranges[mid]
    return None

def asciis(blob,base,pred,limit=250):
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

def collect_xrefs(text,tva,targets):
    hits={t:[] for t in targets}
    for pref in LEA_PREFIXES:
        inst=len(pref)+4;start=0
        while True:
            i=text.find(pref,start)
            if i<0:break
            if i+inst<=len(text):
                disp=struct.unpack_from('<i',text,i+len(pref))[0];tgt=tva+i+inst+disp
                if tgt in hits and len(hits[tgt])<16:hits[tgt].append(tva+i)
            start=i+1
    return hits

rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    rva,rsz=rt.sections['.rdata'];rdata=rt.code(rva,rsz)
    strings=asciis(rdata,rva,lambda s:bool(NARROW.search(s)),limit=250)
    # exact extra needles that the regex might miss
    extra_needles=(b'SEVERITY',b'severity',b'Severity',b'ALERT_SEVERITY',b'CRISIS_SEVERITY',b'PRIORITY',b'CRITICAL')
    extras=[]
    for needle in extra_needles:
        off=0;n=0
        while n<12:
            i=rdata.find(needle,off)
            if i<0:break
            s=i
            while s>0 and 32<=rdata[s-1]<127:s-=1
            t=i
            while t<len(rdata) and 32<=rdata[t]<127:t+=1
            text=rdata[s:t].decode('ascii','replace')
            extras.append({'needle':needle.decode('latin1'),'rva':hex(rva+s),'text':text})
            off=i+1;n+=1
    tva,tsz=rt.sections['.text'];text=rt.code(tva,tsz)
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    targets=sorted({int(s['rva'],16) for s in strings+[{'rva':x['rva']} for x in extras]})
    xmap=collect_xrefs(text,tva,set(targets))
    named=[]
    seen=set()
    for row in strings+extras:
        ev=int(row['rva'],16)
        if ev in seen:continue
        seen.add(ev)
        sites=xmap.get(ev,[])
        funcs=[]
        for site in sites:
            pr=pdata_of(ranges,site)
            funcs.append({'site':hex(site),'pdata':[hex(x) for x in pr] if pr else None,'window':(pr[1]-pr[0]) if pr else None})
        rec={'rva':hex(ev),'text':row['text'],'xrefs':[hex(s) for s in sites],'functions':funcs}
        named.append(rec)
    # RTTI short names in .data
    dva,dsz=rt.sections['.data'];data=rt.code(dva,dsz)
    rtti=[];off=0
    while len(rtti)<40:
        i=data.find(b'.?AV',off)
        if i<0:break
        t=i
        while t<len(data) and 32<=data[t]<127:t+=1
        name=data[i:t].decode('ascii','replace')
        if len(name)<80 and any(k in name for k in ('Severity','CAlert','CCrisis','Priority')) and 'lambda' not in name and 'Func_impl' not in name:
            rtti.append({'name':name,'rva':hex(dva+i)})
        off=i+4
    # Already-qualified witness only: same theatre group, same 3/25 members, alert3/4 +0x448, notes hash control.
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    tp=r.array(rt.country+0x168,64)[0];r.require(tp,'CTheatre')
    tg=r.array(tp+0xc8,128)[0];r.require(tg,'CTheaterGroup')
    og=r.array(tg+0x48,128)[0];r.require(og,'COrdersGroup')
    members=r.array(og+0x50,256);assert len(members)==25
    hours=r.i(rt.base+0x33e3678);threshold=struct.unpack('<q',r.exact(rt.base+0x33e3e00,8))[0]
    assert (hours,threshold)==(72,99000)
    controls=[]
    for member in members[:3]:
        u=member-0xb8;r.require(u,'CArmy');assert r.i(u+0x18)==51 and r.i(u+0x1e0)==3 and r.q(u+0xc0)==og
        assert r.q(r.q(member)+0x20)==rt.base+0xc4f050 and r.q(r.q(u)+0x40)==rt.base+0x20f350
        pp=r.q(u+0x1f0);r.require(pp,'CProvince');pid=r.i(u+0x28);assert r.i(pp+0xa4)==pid
        source=struct.unpack('<q',r.exact(u+0x40,8))[0]
        effective,out,bucket=supply(source,struct.unpack('<q',r.exact(u+0x600,8))[0],struct.unpack('<q',r.exact(u+0x610,8))[0],hours,threshold,bool(r.q(u+0x2f8)))
        controls.append(dict(unit_id=r.i(u+0x1c),province_id=pid,source_raw=source,effective_raw=effective,out_of_supply=out,native_bucket=bucket))
    by={x['unit_id']:x for x in controls}
    assert set(by)=={500,374,479}
    assert (by[479]['province_id'],by[479]['source_raw'],by[479]['effective_raw'],by[479]['out_of_supply'],by[479]['native_bucket'])==(1780,11335,11335,True,0)
    assert (by[374]['source_raw'],by[374]['effective_raw'],by[374]['out_of_supply'],by[374]['native_bucket'])==(100000,100000,False,2)
    manager=r.q(rt.idler+0x7a8)
    names={};param448={};active={};note_raw=None
    for aid,name in [(3,'alert_low_supply'),(4,'alert_very_low_supply')]:
        assert r.string(manager+aid*0x468+0x410)==name
        names[str(aid)]=name
        param448['master_'+str(aid)]=struct.unpack('<I',r.exact(manager+aid*0x468+0x448,4))[0]
        ptr,cap,n=struct.unpack('<QII',r.exact(manager+(aid+0xf0e)*24,16));assert 0<=n<=cap<=32
        keys=[];entries=[]
        for j in range(n):
            ep=ptr+j*0x468;k=struct.unpack('<QQQQ',r.exact(ep+0x438,32));assert r.string(ep+0x410)==name
            p448=struct.unpack('<I',r.exact(ep+0x448,4))[0]
            keys.append((k[0],k[1],k[3]));entries.append({'entry':hex(ep),'key0':k[0],'key_group':hex(k[1]),'key3':k[3],'field_448':p448})
            if aid==4 and (k[0],k[1],k[3])==(0,tg,0):
                assert note_raw is None
                b=r.exact(ep+0x28,32);length,c=struct.unpack_from('<QQ',b,16)
                assert 0<length<=4096 and length<=c<=1048576
                note_raw=b[:length] if c<=15 else r.exact(struct.unpack_from('<Q',b)[0],length)
        active[str(aid)]={'count':n,'keys':keys,'entries':entries}
    assert (0,tg,0) in active['4']['keys'] and (0,tg,0) not in active['3']['keys']
    assert note_raw is not None and len(note_raw)==672 and H(note_raw)=='baea0542d50eaec437826773d8070fcd6a1a7c653a7bd0c6b846b5b4c8f44fba'
    # Also record master+0x448 for already-known air-base alert IDs 5/6 as a same-parameter contrast only; not a land-crisis expansion or new census.
    for aid,name in [(5,'alert_base_low_supply'),(6,'alert_base_very_low_supply')]:
        assert r.string(manager+aid*0x468+0x410)==name
        names[str(aid)]=name
        param448['master_'+str(aid)]=struct.unpack('<I',r.exact(manager+aid*0x468+0x448,4))[0]
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'named_strings':named,'extra_hits':extras,'rtti':rtti,'controls':controls,'sampled_members':3,'native_member_count':25,'new_units_inspected':0,'names':names,'field_448':param448,'active':active,'note_raw_sha256':H(note_raw),'note_byte_length':len(note_raw),'theater_group':hex(tg),'scope':'Named severity-literal harvest plus already-qualified witness only. field+0x448 is the B61660 r9d registration parameter already rejected as schema severity until independently named. Alert 5/6 masters are same-parameter contrast, not land-crisis feed expansion. Notes hash is an identity control, not a new notes scan. No game mutation.','stable_dependencies':stable}
    (Q/'t231_named_severity_and_witness.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'at_est':out['at_est'],'named':[{'text':s['text'],'rva':s['rva'],'xrefs':s['xrefs'],'pdata':[f['pdata'] for f in s['functions']]} for s in named if s['xrefs'] or NARROW.search(s['text'] or '')],'named_count':len(named),'rtti':rtti,'field_448':param448,'active_summary':{k:{'count':v['count'],'entries':v['entries']} for k,v in active.items()},'controls':controls,'note_raw_sha256':H(note_raw),'stable_dependencies':stable},ensure_ascii=False,indent=2))
finally:
    rt.close()
