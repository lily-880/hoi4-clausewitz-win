# Read-only named frontline-staffing literal/RTTI scan. No game writes/calls/save/UI/time changes.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t229_final_seal.json').read_text(encoding='utf-8'))
for name,h in prev['production_hashes'].items():
    assert H((Q.parent/name).read_bytes())==h
NEEDLES=[
 'MISSING_DIVISIONS','DIVISIONS_MISSING','MISSING_DIVISION','DIVISIONS_REQUIRED','REQUIRED_DIVISIONS',
 'NEEDED_DIVISIONS','DIVISIONS_NEEDED','NEED_DIVISIONS','NEED_MORE_DIVISIONS','NOT_ENOUGH_DIVISIONS',
 'INSUFFICIENT_DIVISIONS','FRONT_CANNOT_HOLD','CANNOT_HOLD_FRONT','CANNOT_HOLD','FRONTLINE_NEED',
 'FRONT_NEED','FRONT_NEEDS','UNITS_NEEDED','UNITS_REQUIRED','DIVISIONS_ASSIGNED','ASSIGNED_DIVISIONS',
 'WANTED_DIVISIONS','DESIRED_DIVISIONS','DESIRED_NR_DIVISIONS','NUM_WANTED_DIVISIONS','NUM_NEEDED_DIVISIONS',
 'FRONT_UNIT_REQUEST','SUBTRACT_FRONTS_FROM_NEED','FRONTAGE_FULL','FRONT_STRENGTH','FRONTLINE_STRENGTH',
 'UNDERSTRENGTH_FRONT','FRONT_MISSING','MISSING_UNITS','REQUIRED_UNITS','RECOMMENDED_DIVISIONS',
 'MIN_NR_DIVISIONS','MAX_NR_DIVISIONS','AI_WANTED_DIVISIONS','AI_DESIRED_DIVISIONS','AI_WANTS_DIVISIONS',
 'ALERT_FRONT','LOW_DIVISIONS','STAFFING','FRONT_UNIT','UNIT_REQUEST','DIVISIONS_TO_ASSIGN',
 'NEEDED_UNITS','NEED_UNIT','FRONT_REQUEST','REQUESTED_DIVISIONS','REQUIRED_NR_DIVISIONS',
 'NR_DIVISIONS_NEEDED','NR_MISSING_DIVISIONS','MISSING_NR_DIVISIONS','DIVISION_SHORTAGE',
 'FRONT_SHORTAGE','SHORTAGE_DIVISIONS','HOLD_FRONT','MAINTAIN_FRONT','FRONT_HOLD',
 'INSUFFICIENT_UNITS','NOT_ENOUGH_UNITS','UNITS_MISSING','ARMY_REQUEST','FRONTLINE_UNITS',
 'FRONTLINE_DIVISIONS','ASSIGNED_UNITS','WANTED_NR_DIVISIONS','TOTAL_WANTED_NR_DIVISIONS',
 'STATE_MINIMUM_DIVISIONS','GARRISON_REQUIRED','REQUIRED_GARRISON','MISSING_GARRISON'
]
# Script tokens already independently named; included as registration clips only, not automatic schema fields.
TOKEN_NAMES={
 'front_unit_request','subtract_fronts_from_need','frontage_full','num_wanted_divisions',
 'desired_nr_divisions','min_nr_divisions','max_nr_divisions','ai_wanted_divisions_factor',
 'ai_wants_divisions','ai_desired_divisions_factor','ai_store_total_wanted_nr_divisions_command',
 'state_minimum_divisions','required_garrison_factor','garrison_required','missing_garrison_law',
 'front_control','front_order','front_armor_score','force_concentration_front_factor',
 'assign_army_to_army_group_front','send_volunteer_divisions_required'
}
LEA_PREFIXES=(b'\x48\x8d\x05',b'\x48\x8d\x0d',b'\x48\x8d\x15',b'\x48\x8d\x1d',b'\x48\x8d\x35',b'\x48\x8d\x3d',
              b'\x4c\x8d\x05',b'\x4c\x8d\x0d',b'\x4c\x8d\x15',b'\x4c\x8d\x1d',b'\x4c\x8d\x35',b'\x4c\x8d\x3d')
RTTI_KEEP=('FRONT','STAFF','SHORTAGE','REQUEST','GARRISON','THEATRE','THEATER','ORDER')
def pdata_of(ranges,rva):
    lo,hi=0,len(ranges)
    while lo<hi:
        mid=(lo+hi)//2
        s,e,_=ranges[mid]
        if rva<s:hi=mid
        elif rva>=e:lo=mid+1
        else:return ranges[mid]
    return None
def extract_ascii(blob,off,limit=96):
    b=blob[off:off+limit].split(b'\0')[0]
    if 3<=len(b)<=95 and all(32<=x<127 for x in b):return b.decode()
    return None
def collect_xrefs(text,tva,targets):
    # Single pass over LEA prefixes; map target RVA -> code sites.
    hits={t:[] for t in targets}
    for pref in LEA_PREFIXES:
        inst=len(pref)+4;start=0
        while True:
            i=text.find(pref,start)
            if i<0:break
            if i+inst<=len(text):
                disp=struct.unpack_from('<i',text,i+len(pref))[0]
                tgt=tva+i+inst+disp
                if tgt in hits and len(hits[tgt])<32:
                    hits[tgt].append(tva+i)
            start=i+1
    return hits
rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:
        assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
    rva,rsz=rt.sections['.rdata'];blob=rt.code(rva,rsz)
    tva,tsz=rt.sections['.text'];text=rt.code(tva,tsz)
    pva,psz=rt.sections['.pdata'];pd=rt.code(pva,psz)
    ranges=[struct.unpack_from('<III',pd,j) for j in range(0,len(pd)-11,12)]
    candidates=[]
    seen=set()
    for needle in NEEDLES:
        raw=needle.encode();off=0;count=0
        while True:
            i=blob.find(raw,off)
            if i<0:break
            s0=i
            while s0>0 and 32<=blob[s0-1]<127:s0-=1
            full=extract_ascii(blob,s0,96)
            ev=rva+s0
            key=(full or needle,ev)
            if key not in seen and full:
                candidates.append({'needle':needle,'rva':ev,'text':full,'exact':full==needle})
                seen.add(key);count+=1
            off=i+1
            if count>=12:break
    xrefmap=collect_xrefs(text,tva,{c['rva'] for c in candidates})
    literals=[]
    for c in candidates:
        xrefs=xrefmap.get(c['rva'],[])
        funcs=[]
        for site in xrefs:
            pr=pdata_of(ranges,site)
            funcs.append({'site':hex(site),'pdata':[hex(x) for x in pr] if pr else None,'window':(pr[1]-pr[0]) if pr else None})
        literals.append({'needle':c['needle'],'rva':hex(c['rva']),'text':c['text'],'exact':c['exact'],'xrefs':[hex(x) for x in xrefs],'functions':funcs})
    # RTTI class names in rdata
    rtti=[];roff=0;needle=b'.?AV'
    while True:
        i=blob.find(needle,roff)
        if i<0:break
        name=extract_ascii(blob,i,160)
        if name:
            u=name.upper()
            if any(k in u for k in RTTI_KEEP) and any(k in u for k in ('FRONT','STAFF','SHORTAGE','REQUEST','GARRISON')):
                rtti.append({'rva':hex(rva+i),'name':name})
        roff=i+4
        if len(rtti)>=80:break
    # Token registration clips; never run a serializer.
    tokens=[];cs_needed=False
    mp=json.loads((Q/'t163_script_token_map.json').read_text(encoding='utf-8'))
    from capstone import Cs,CS_ARCH_X86,CS_MODE_64
    cs=Cs(CS_ARCH_X86,CS_MODE_64)
    for row in mp:
        if row['name'] not in TOKEN_NAMES:continue
        va=int(row['registration_rva'],16);b=rt.code(va,64)
        tokens.append(dict(row,raw_hex=b.hex(),asm=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(b,va)]))
    # Bounded current own-theatre/group class inventory only; no unit-count substitution, no world front heap walk, no empty-plan resampling.
    r=rt.reader();assert country_tag(r,rt.gs,rt.index,rt.country)=='SOV'
    theatres=r.array(rt.country+0x168,64)
    theatre_rows=[]
    for tp in theatres:
        r.q(tp);tc=rt.cls(tp);assert 'CTheatre' in tc
        groups=r.array(tp+0xc8,128)
        group_rows=[]
        for tg in groups:
            r.q(tg);gc=rt.cls(tg)
            orders=r.array(tg+0x48,128)
            order_rows=[]
            for og in orders:
                r.q(og);oc=rt.cls(og)
                members=r.array(og+0x50,256)
                # look only at a tight header window for CFront* / CFrontSection* identity, not a desired-force calculation
                window=r.exact(og,0x120)
                front_hits=[]
                for off in range(0,0x120,8):
                    p=struct.unpack_from('<Q',window,off)[0]
                    if p==0 or p==0x100000035: continue
                    try:
                        c=rt.cls(p)
                    except Exception:
                        continue
                    if 'Front' in c or 'Request' in c:
                        front_hits.append({'offset':hex(off),'ptr':hex(p),'class':c})
                order_rows.append({'orders_group':hex(og),'class':oc,'member_count':len(members),'frontish_header_hits':front_hits,'plan_slot_98':hex(r.q(og+0x98))})
            # theatre-group header window
            gwindow=r.exact(tg,0x100)
            ghits=[]
            for off in range(0,0x100,8):
                p=struct.unpack_from('<Q',gwindow,off)[0]
                if not p: continue
                try:c=rt.cls(p)
                except Exception: continue
                if 'Front' in c or 'Request' in c:
                    ghits.append({'offset':hex(off),'ptr':hex(p),'class':c})
            group_rows.append({'theater_group':hex(tg),'class':gc,'orders_groups':order_rows,'frontish_header_hits':ghits})
        twindow=r.exact(tp,0x180)
        thits=[]
        for off in range(0,0x180,8):
            p=struct.unpack_from('<Q',twindow,off)[0]
            if not p: continue
            try:c=rt.cls(p)
            except Exception: continue
            if 'Front' in c or 'Request' in c:
                thits.append({'offset':hex(off),'ptr':hex(p),'class':c})
        theatre_rows.append({'theatre':hex(tp),'class':tc,'groups':group_rows,'frontish_header_hits':thits,'group_count':len(groups)})
    stable=r.stable();after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'literals':literals,'rtti':rtti,'token_registration_clips':tokens,'own_theatre_inventory':theatre_rows,'scope':'Named literal/RTTI/token registration only. Header-window class inventory is membership discovery, not a missing-division value. Desired/wanted/needed-force tokens are not automatically schema missing_divisions. No empty-plan list resampling, no world front heap walk, no game mutation.','stable_dependencies':stable}
    (Q/'t230_named_staffing_literal_scan.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary={'at_est':out['at_est'],'literal_count':len(literals),'literals':[{k:L[k] for k in ('needle','rva','text','exact','xrefs')} for L in literals],'rtti':rtti,'token_names':[t['name'] for t in tokens],'theatres':[{'theatre':t['theatre'],'group_count':t['group_count'],'frontish_header_hits':t['frontish_header_hits'],'groups':[{'class':g['class'],'frontish_header_hits':g['frontish_header_hits'],'orders':[{'class':o['class'],'member_count':o['member_count'],'frontish_header_hits':o['frontish_header_hits']} for o in g['orders_groups']]} for g in t['groups']]} for t in theatre_rows],'stable_dependencies':stable}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
finally:
    rt.close()
