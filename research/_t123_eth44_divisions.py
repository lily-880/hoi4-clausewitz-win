import json, os, struct, sys, collections, re, pathlib
sys.path.insert(0, os.path.join(os.getcwd(), "calling"))
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"

import config, offsets as O
from gamestate import _pdx_array
from mem import Proc, find_pid

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])

CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_DIV_TEMPLATE = 0x3B8
TMPL_NAME = 0x20
CO_ARMIES = 0x290
ETH_IDX = 44

def u32(a):
    b=p.try_read(a,4)
    return struct.unpack_from("<I",b,0)[0] if b else None
def i32(a):
    b=p.try_read(a,4)
    return struct.unpack_from("<i",b,0)[0] if b else None
def u64(a):
    b=p.try_read(a,8)
    return struct.unpack_from("<Q",b,0)[0] if b else None
def read_utf8(addr,n=96):
    b=p.try_read(addr,n)
    if not b: return None
    s=b.split(b"\0",1)[0]
    try:
        t=s.decode("utf-8")
    except Exception:
        return None
    return t or None

def read_tmpl_name(army_ptr):
    tmpl=u64(army_ptr+CA_DIV_TEMPLATE)
    if not tmpl: return None
    ptr=u64(tmpl+TMPL_NAME)
    if ptr and 0x10000 < ptr < 0x7FFFFFFFFFFF:
        return read_utf8(ptr)
    return read_utf8(tmpl+TMPL_NAME)

cptr=u64(countries["data"]+ETH_IDX*8)
armies=_pdx_array(p,cptr+CO_ARMIES)
live=[]
for i in range(armies["size"]):
    ap=u64(armies["data"]+i*8)
    live.append({
        "slot": i,
        "ptr": hex(ap) if ap else None,
        "province": u32(ap+CA_PROVINCE_ID) if ap else None,
        "country_tag_field": i32(ap+CA_COUNTRY_TAG) if ap else None,
        "template": read_tmpl_name(ap) if ap else None,
        "vt": hex(u64(ap)) if ap else None,
    })

# parse OOB names
oob_path=pathlib.Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\history\units\ETH_1936_bba.txt")
text=oob_path.read_text(encoding="utf-8",errors="replace")
parts=re.split(r"(?m)(?=^\s*division\s*=\s*\{)", text)
oob=[]
for part in parts:
    if not part.strip().startswith("division"):
        continue
    name=None
    m=re.search(r'name\s*=\s*"([^"]+)"', part)
    if m: name=m.group(1)
    loc=re.search(r"location\s*=\s*(\d+)", part)
    tmpl=re.search(r'division_template\s*=\s*"([^"]+)"', part)
    if loc and tmpl:
        oob.append({"name": name, "province": int(loc.group(1)), "template": tmpl.group(1)})

# greedy match live to remaining OOB by (template, province)
remaining=list(enumerate(oob))
matched=[]
unmatched_live=[]
used=set()
for unit in live:
    hit=None
    for j,(oi,row) in enumerate(remaining):
        if oi in used: continue
        if row["template"]==unit["template"] and row["province"]==unit["province"]:
            hit=(oi,row); break
    if hit:
        used.add(hit[0])
        matched.append({**unit, "oob_name": hit[1]["name"]})
    else:
        unmatched_live.append(unit)
unmatched_oob=[row for i,row in enumerate(oob) if i not in used]

# province names from state files (best-effort: history/states *.txt containing the id as a province)
prov_ids=sorted({u["province"] for u in live if u["province"]})
state_dir=pathlib.Path(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\history\states")
prov_place={}
# Use localisation or province map? Faster: scan state files for provinces={ ... id ... } and state name
for fp in state_dir.glob("*.txt"):
    t=fp.read_text(encoding="utf-8",errors="replace")
    m=re.search(r"provinces\s*=\s*\{([^}]+)\}", t, re.S)
    if not m: continue
    ids=set(int(x) for x in re.findall(r"\d+", m.group(1)))
    # state name from filename like 271-Ethiopia.txt or id/name
    sm=re.search(r"^(\d+)[-_ ]?(.*)\.txt$", fp.name)
    label=sm.group(2).strip() if sm else fp.stem
    for pid in ids:
        if pid in prov_ids:
            prov_place[pid]=label

# Hunt a player/human flag: compare byte histograms of ETH vs SPR vs a few AI
# Look for offsets where ETH is unique among first 80 countries, or uniquely 1/true
def country_blob(idx, n=0x700):
    cp=u64(countries["data"]+idx*8)
    return cp, (p.try_read(cp,n) or b"")

candidates=[]
# also dump ints around GS_PLAYER_TAG and any field equal to 44
gs_eq_44=[]
for off in range(0x400, 0x700, 4):
    v=i32(gs+off)
    if v==44:
        gs_eq_44.append(hex(off))
    if v==15 and off!=0x518:
        pass

# unique byte/int flags: for each 4-byte offset in 0x000-0x6ff, value at ETH, SPR, and uniqueness
eth_ptr, eth_blob = country_blob(ETH_IDX)
spr_ptr, spr_blob = country_blob(15)
# sample other countries with armies
sample_idx=[0,1,2,3,4,5,7,10,20,30,40,43,45,50,51,97,100,200]
sample_blobs=[]
for idx in sample_idx:
    cp,b=country_blob(idx)
    if b: sample_blobs.append((idx,b))

unique_i32=[]
if len(eth_blob)>=0x6FC and len(spr_blob)>=0x6FC:
    for off in range(0, 0x6FC, 4):
        ev=struct.unpack_from("<i", eth_blob, off)[0]
        sv=struct.unpack_from("<i", spr_blob, off)[0]
        # look for 1 vs 0 style flags, or ev==1 and others 0
        others=[]
        for idx,b in sample_blobs:
            if len(b)>off+3:
                others.append(struct.unpack_from("<i", b, off)[0])
        # ETH unique among samples+SPR
        if ev in (0,1) and ev!=sv and all(v!=ev for v in others):
            unique_i32.append({"off":hex(off), "eth":ev, "spr":sv, "sample":others[:8]})

# tag field on armies already showed country index? check ETH army country_tag
# strings on ETH country object
def strings_near(ptr,n=0x800):
    b=p.try_read(ptr,n) or b""
    out=[]; i=0
    while i<len(b):
        if 32<=b[i]<127:
            j=i
            while j<len(b) and 32<=b[j]<127:
                j+=1
            if j-i>=3:
                s=b[i:j].decode("ascii","ignore")
                if any(c.isalpha() for c in s):
                    out.append({"off":i,"s":s[:80]})
            i=j+1
        else:
            i+=1
    return out

out={
    "eth_index": ETH_IDX,
    "eth_cptr": hex(cptr),
    "live_count": len(live),
    "oob_count": len(oob),
    "matched": matched,
    "unmatched_live": unmatched_live,
    "unmatched_oob": unmatched_oob,
    "prov_place": {str(k):v for k,v in prov_place.items()},
    "gs_fields_eq_44": gs_eq_44,
    "player_flag_unique_i32": unique_i32[:40],
    "eth_strings": strings_near(cptr,0x200),
    "claimed_player_still": i32(gs+0x518),
    "eth_army_country_tag_set": sorted({u["country_tag_field"] for u in live}),
}
path=r"research\_t123_eth44_divisions.json"
with open(path,"w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=2)

print("LIVE",len(live),"OOB",len(oob),"MATCHED",len(matched),"UNMATCHED_LIVE",len(unmatched_live),"UNMATCHED_OOB",len(unmatched_oob))
print("PLACES",prov_place)
print("GS_EQ_44",gs_eq_44)
print("UNIQUE_FLAGS",len(unique_i32))
for x in unique_i32[:25]:
    print(x)
print("ETH_TAG_FIELD",out["eth_army_country_tag_set"])
print("STRINGS",out["eth_strings"][:15])
for u in matched:
    print(f"{u['slot']:02d} p={u['province']} {u['template']} | {u['oob_name']}")
if unmatched_live:
    print("UNMATCHED LIVE")
    for u in unmatched_live:
        print(u)
if unmatched_oob:
    print("UNMATCHED OOB")
    for u in unmatched_oob:
        print(u)
