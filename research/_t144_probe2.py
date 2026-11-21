import os, sys, json, struct, math, collections
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import _pdx_array, resolve_player_country, _rtti_name_from_vtable
from handle import HANDLE_TYPE_ARMY
from pe import PE

OUT = Path("research/_t144_probe2.json")
FIXED = 100000
CA_HANDLE = 0x18
DUMP = 0xA00

EXPECTED = {
    1829: dict(name="Kebur Zabagna", eq=1.0, xp=0.2, officer=None, mp=5000, max_org=62.0, width=10, bat=5),
    1830: dict(name="1 Gojjam Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1831: dict(name="1 Wolqayt Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=70.0, width=8, bat=4),
    1832: dict(name="1 Semien Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=70.0, width=8, bat=4),
    1833: dict(name="1 Amino Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1834: dict(name="1 Gubba Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1835: dict(name="1 Gurage Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1836: dict(name="1 Jimma Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1837: dict(name="1 Om Hajer Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1838: dict(name="1 Sela Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1839: dict(name="1 Welega Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, width=8, bat=4),
    1840: dict(name="1 Begemder Sefari", eq=0.6, xp=0.05, officer="Wondosson Kassa", mp=6000, max_org=45.0, width=12, bat=6),
    1841: dict(name="1 Tigray Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, width=12, bat=6),
    1842: dict(name="1 Wag Sefari", eq=0.45, xp=0.05, officer="Haile Kebbede", mp=6000, max_org=45.0, width=12, bat=6),
    1843: dict(name="1 Welega-Ardjo Sefari", eq=1.0, xp=0.25, officer="Makonnen Demissie", mp=6000, max_org=45.0, width=12, bat=6),
    1844: dict(name="1 Kaffa Sefari", eq=0.6, xp=0.05, officer="Getachew Abate", mp=6000, max_org=45.0, width=12, bat=6),
    1845: dict(name="1 Ogaden Sefari", eq=0.6, xp=0.05, officer="Afawarq Walda Samayat", mp=6000, max_org=45.0, width=12, bat=6),
    1846: dict(name="1 Hararghe Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, width=12, bat=6),
    1847: dict(name="1 Illubabor Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, width=12, bat=6),
    1848: dict(name="1 Bale Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, width=12, bat=6),
    1849: dict(name="1 Sidamo Sefari", eq=0.9, xp=0.2, officer=None, mp=6000, max_org=45.0, width=12, bat=6),
}

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
exe = getattr(p, "image_path", None) or r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(exe)

def u32(a):
    x = p.try_read(a, 4)
    return struct.unpack_from("<I", x, 0)[0] if x else None
def i32(a):
    x = p.try_read(a, 4)
    return struct.unpack_from("<i", x, 0)[0] if x else None
def u64(a):
    x = p.try_read(a, 8)
    return struct.unpack_from("<Q", x, 0)[0] if x else None
def f32(a):
    x = p.try_read(a, 4)
    if not x: return None
    v = struct.unpack_from("<f", x, 0)[0]
    return v if math.isfinite(v) else None
def looks_ptr(x):
    return bool(x) and 0x10000 < x < 0x7FFFFFFFFFFF
def rtti_name(vt):
    if not vt or vt < p.base: return None
    try:
        name = _rtti_name_from_vtable(pe, vt - p.base)
    except Exception:
        return None
    if name and name.startswith(".?AV") and name.endswith("@@"):
        return name[4:-2]
    if name and name.startswith(".?AU") and name.endswith("@@"):
        return name[4:-2]
    return name
def class_of(addr):
    return rtti_name(u64(addr)) if looks_ptr(addr) else None
def read_utf8(addr, n=128):
    raw = p.try_read(addr, n)
    if not raw: return None
    s = raw.split(b"\0", 1)[0]
    if not s: return None
    try:
        t = s.decode("utf-8")
    except Exception:
        return None
    if not all(ch.isprintable() or ch in " \t" for ch in t):
        return None
    return t or None
def read_pdx_string(addr):
    if not addr: return None
    # MSVC SSO: if size/cap indicates SSO, inline at addr; else pointer at addr
    # Clausewitz often uses pointer-or-inline: if looks_ptr, follow.
    ptr = u64(addr)
    if looks_ptr(ptr):
        s = read_utf8(ptr)
        if s: return s
    # SSO inline 16 bytes + size at +16?
    s = read_utf8(addr, 16)
    if s: return s
    sz = u32(addr + 16)
    cap = u32(addr + 20)
    if sz and sz < 128 and cap and cap >= sz:
        if looks_ptr(ptr):
            return read_utf8(ptr, sz+1)
        return read_utf8(addr, sz+1)
    return None

def pdx_array(addr):
    data, cap, size = u64(addr), u32(addr+8), u32(addr+12)
    if not looks_ptr(data) or cap is None or size is None:
        return None
    if cap > 8000 or size > cap:
        return None
    return {"addr": addr, "data": data, "cap": cap, "size": size}

resolved = resolve_player_country(p, gs)
idx = resolved["player_index"]
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
cptr = u64(countries["data"] + idx * 8)
armies = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_ARMIES"])
units = []
for slot in range(armies["size"]):
    ap = u64(armies["data"] + slot * 8)
    if not ap: continue
    uid = u32(ap + CA_HANDLE + 4)
    units.append({"id": uid, "ptr": ap, "exp": EXPECTED[uid]})

# ---- list arrays on first and all units ----
def arrays_on(ap):
    found = []
    for off in range(0, DUMP-15, 8):
        arr = pdx_array(ap + off)
        if not arr: continue
        # require allocator or reasonable cap
        alloc = class_of(u64(ap + off + 16))
        if arr["size"] == 0 and arr["cap"] == 0:
            continue
        if alloc != "CPdxNewDeleteAllocator" and arr["size"] == 0:
            continue
        elems_u32, elems_ptr = [], []
        n = min(arr["size"], 12)
        raw = p.try_read(arr["data"], n * 8) or b""
        for i in range(n):
            if (i+1)*4 <= len(raw):
                elems_u32.append(struct.unpack_from("<I", raw, i*4)[0])
            if (i+1)*8 <= len(raw):
                pv = struct.unpack_from("<Q", raw, i*8)[0]
                if looks_ptr(pv):
                    elems_ptr.append({"ptr": hex(pv), "rtti": class_of(pv)})
        found.append({
            "off": off, "size": arr["size"], "cap": arr["cap"],
            "alloc": alloc, "u32": elems_u32,
            "fixed": [round(v/FIXED, 5) for v in elems_u32 if v < 50*FIXED],
            "ptrs": elems_ptr,
        })
    return found

# union of array offs
all_arr_offs = collections.Counter()
arr_by_unit = {}
for u in units:
    arrs = arrays_on(u["ptr"])
    arr_by_unit[u["id"]] = arrs
    for a in arrs:
        all_arr_offs[a["off"]] += 1

# summarize each array off across units
arr_summary = []
for off, cnt in sorted(all_arr_offs.items()):
    rows = []
    for u in units:
        hit = next((a for a in arr_by_unit[u["id"]] if a["off"]==off), None)
        rows.append({"id": u["id"], "name": u["exp"]["name"], "eq": u["exp"]["eq"], "xp": u["exp"]["xp"], "mp": u["exp"]["mp"], "org": u["exp"]["max_org"], "bat": u["exp"]["bat"], "arr": hit})
    # if u32[0]/FIXED correlates with eq or first values interesting
    arr_summary.append({"off": off, "present": cnt, "rows": rows})

# ---- fixed-point / int / float scan vs expected ----
def mae(xs, ys):
    d=[abs(a-b) for a,b in zip(xs,ys) if a is not None and b is not None]
    return (sum(d)/len(d)) if d else 999

eqs=[u["exp"]["eq"] for u in units]
xps=[u["exp"]["xp"] for u in units]
mps=[u["exp"]["mp"] for u in units]
orgs=[u["exp"]["max_org"] for u in units]
bats=[u["exp"]["bat"] for u in units]
eq_amt=[u["exp"]["bat"]*u["exp"]["eq"] for u in units]  # 4*0.8=3.2 etc, kebur 5?

hits={"eq_ratio":[], "eq_amount":[], "xp":[], "org":[], "org_frac":[], "mp":[], "mp_k":[], "supply01":[]}
for off in range(0, DUMP-3, 4):
    raw_i, raw_f, raw_fx = [], [], []
    ok=True
    for u in units:
        iv=i32(u["ptr"]+off); fv=f32(u["ptr"]+off)
        raw_i.append(iv); raw_f.append(fv)
        raw_fx.append(None if iv is None else iv/FIXED)
    # skip pointer-ish large
    def consider(vals, target, key, tol, extra=None):
        if any(v is None for v in vals): return
        err=mae(vals,target)
        n=sum(abs(a-b)<=tol for a,b in zip(vals,target))
        if n>=18 or err<=tol:
            rec={"off":off,"n":n,"mae":round(err,6),"values":[round(v,5) if isinstance(v,float) else v for v in vals]}
            if extra: rec.update(extra)
            hits[key].append(rec)
    consider(raw_f, eqs, "eq_ratio", 0.03, {"src":"f32"})
    consider(raw_fx, eqs, "eq_ratio", 0.03, {"src":"fixed"})
    consider(raw_f, xps, "xp", 0.03, {"src":"f32"})
    consider(raw_fx, xps, "xp", 0.03, {"src":"fixed"})
    consider(raw_i, [int(round(x*FIXED)) for x in xps], "xp", 0, {"src":"i32_xp_fixedraw"})
    consider(raw_f, orgs, "org", 0.6, {"src":"f32"})
    consider(raw_fx, orgs, "org", 0.6, {"src":"fixed"})
    consider(raw_i, [int(o) for o in orgs], "org", 0, {"src":"i32"})
    consider(raw_i, [int(o*1000) for o in orgs], "org", 0, {"src":"i32_x1000"})
    consider(raw_f, eqs, "eq_ratio", 0.03)  # already
    consider(raw_f, mps, "mp", 1, {"src":"f32"})
    consider(raw_i, mps, "mp", 0, {"src":"i32"})
    consider(raw_i, [m*1000 for m in mps], "mp_k", 0, {"src":"i32_x1000"})
    consider(raw_fx, eq_amt, "eq_amount", 0.08, {"src":"fixed"})
    consider(raw_f, eq_amt, "eq_amount", 0.08, {"src":"f32"})

# sort
for k in hits:
    hits[k]=sorted(hits[k], key=lambda r:(-r.get("n",0), r.get("mae",9)))[:8]

# ---- CArmy* fields ----
carmy_ptrs={}
for off in (1048, 1280, 1600):
    rows=[]
    for u in units:
        pv=u64(u["ptr"]+off)
        rec={"id":u["id"], "ptr": hex(pv) if looks_ptr(pv) else pv, "rtti": class_of(pv) if looks_ptr(pv) else None}
        if looks_ptr(pv):
            rec["is_self"]= pv==u["ptr"]
            rec["other_eth_id"]= next((x["id"] for x in units if x["ptr"]==pv), None)
            rec["other_handle"]= u32(pv+CA_HANDLE+4) if class_of(pv)=="CArmy" else None
            rec["other_tag"]= i32(pv+0x1E0) if class_of(pv)=="CArmy" else None
        rows.append(rec)
    carmy_ptrs[off]=rows

# ---- officer block ----
officers=[]
for u in units:
    op=u64(u["ptr"]+0x568)
    oid=i32(u["ptr"]+0x564)
    rec={"id":u["id"], "expected":u["exp"]["officer"], "leader_field":oid, "obj": hex(op) if looks_ptr(op) else op, "rtti": class_of(op)}
    if looks_ptr(op):
        # dump first 0x80 as strings and ints
        rec["i32"]={hex(i): i32(op+i) for i in range(0, 0x80, 4)}
        rec["strs"]=[]
        for s_off in range(0, 0x80, 8):
            s=read_pdx_string(op+s_off)
            if s and len(s)>=3:
                rec["strs"].append({"off":s_off,"s":s})
        rec["name_plus0"]=read_pdx_string(op)
        rec["name_plus8"]=read_pdx_string(op+8)
        rec["name_plus16"]=read_pdx_string(op+16)
        rec["name_plus24"]=read_pdx_string(op+24)
    officers.append(rec)

# ---- character manager lookup for 68853.. ----
cm = u64(gs + O.HYPOTHESIS_STRUCT["GS_CHARACTER_MANAGER"])
cm_info={"ptr": hex(cm) if cm else None, "rtti": class_of(cm), "hits": []}
if looks_ptr(cm):
    chars=_pdx_array(p, cm + O.HYPOTHESIS_STRUCT["CM_CHARACTERS"])
    active=_pdx_array(p, cm + O.HYPOTHESIS_STRUCT["CM_CHARACTERS_ACTIVE"])
    cm_info["n_chars"]=None if not chars else chars.get("size")
    cm_info["n_active"]=None if not active else active.get("size")
    want=set(r["leader_field"] for r in officers if r["leader_field"] not in (None,-1,0))
    # scan first 0x80 of each character? too many 9661. Instead, if there's an id map.
    # try: maybe 68853 is a direct handle or index. Try resolve as various types? skip heavy.
    # Search only active 2361 for matching i32 id and names
    if active and active.get("data") and want:
        found=[]
        for i in range(active["size"]):
            cp=u64(active["data"]+i*8)
            if not looks_ptr(cp): continue
            blob=p.try_read(cp, 0x100) or b""
            ids_here=[]
            for off in range(0, len(blob)-3, 4):
                val=struct.unpack_from("<i", blob, off)[0]
                if val in want:
                    ids_here.append(off)
            if ids_here:
                strs=[]
                for s_off in range(0, 0x100, 8):
                    s=read_pdx_string(cp+s_off)
                    if s and len(s)>=3 and any(c.isalpha() for c in s):
                        strs.append({"off":s_off,"s":s})
                found.append({"i":i,"ptr":hex(cp),"rtti":class_of(cp),"id_offs":ids_here,"strs":strs[:8]})
                if len(found)>=12:
                    break
        cm_info["hits"]=found

# ---- theatre fronts / other arrays for formation ----
theatres=_pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_THEATRES"])
formation={"theatres": [], "country_array_classes": []}
if theatres and theatres.get("data"):
    for i in range(theatres["size"]):
        th=u64(theatres["data"]+i*8)
        rec={"i":i,"ptr":hex(th) if th else None,"rtti":class_of(th),"arrays":[]}
        if looks_ptr(th):
            for off in range(0, 0x200, 8):
                arr=pdx_array(th+off)
                if not arr or arr["size"]==0: continue
                n=min(arr["size"], 6)
                raw=p.try_read(arr["data"], n*8) or b""
                ptrs=[]
                for j in range(n):
                    if (j+1)*8<=len(raw):
                        pv=struct.unpack_from("<Q", raw, j*8)[0]
                        if looks_ptr(pv):
                            ptrs.append({"rtti":class_of(pv),"ptr":hex(pv)})
                rec["arrays"].append({"off":off,"size":arr["size"],"cap":arr["cap"],"sample":ptrs})
        formation["theatres"].append(rec)

# country-level arrays that point to army group / unit / front
for off in range(0x100, 0x700, 8):
    arr=_pdx_array(p, cptr+off)
    if not arr or arr.get("size",0)==0 or arr["size"]>5000: continue
    n=min(arr["size"], 5)
    classes=[]
    if arr.get("data"):
        for j in range(n):
            pv=u64(arr["data"]+j*8)
            if looks_ptr(pv):
                classes.append(class_of(pv))
    uniq=[c for c in dict.fromkeys(classes) if c]
    if uniq:
        formation["country_array_classes"].append({"off":off,"size":arr["size"],"cap":arr.get("capacity"),"rtti":uniq})

# ---- follow 0x138 CSubUnitDefinition and hunt instance arrays ----
sub = []
for u in units[:3]+[units[11], units[13], units[0]]:  # sample variety
    ap=u["ptr"]
    defn=u64(ap+0x138)
    rec={"id":u["id"],"def":hex(defn) if defn else None,"def_rtti":class_of(defn)}
    # any array whose pointers are CSubUnit / similar
    rec["subunitish"]=[]
    for a in arr_by_unit[u["id"]]:
        if a["ptrs"]:
            rt=sorted({x["rtti"] for x in a["ptrs"] if x["rtti"]})
            if any(r and ("SubUnit" in r or "Unit" in r or "Battalion" in r or "Regiment" in r) for r in rt):
                rec["subunitish"].append({"off":a["off"],"size":a["size"],"rtti":rt})
        # also if size == battalion count
        if a["size"]==u["exp"]["bat"] or a["size"]==u["exp"]["bat"]+1:
            rec.setdefault("size_eq_bat", []).append({"off":a["off"],"size":a["size"],"u32":a["u32"],"fixed":a["fixed"],"ptrs":a["ptrs"]})
    sub.append(rec)

# also size==bat across all units for common offs
bat_offs=[]
for off in all_arr_offs:
    ok=0
    rows=[]
    for u in units:
        a=next((x for x in arr_by_unit[u["id"]] if x["off"]==off), None)
        if a and a["size"]==u["exp"]["bat"]:
            ok+=1
            rows.append({"id":u["id"],"size":a["size"],"u32":a["u32"],"fixed":a["fixed"],"ptrs":a["ptrs"][:3]})
    if ok>=18:
        bat_offs.append({"off":off,"match":ok,"rows":rows})

out={
    "hits":hits,
    "eq_amount_expected": eq_amt,
    "carmy_ptrs":carmy_ptrs,
    "officers":officers,
    "characters":cm_info,
    "formation":formation,
    "sub_sample":sub,
    "bat_arrays":bat_offs,
    "array_offs": sorted(all_arr_offs.items()),
    # compact array view: only offs with varying u32/fixed or ptr rtti
    "arrays_interesting": [],
}
for s in arr_summary:
    off=s["off"]
    sizes=[(r["arr"] or {}).get("size") for r in s["rows"]]
    fixed=[(r["arr"] or {}).get("fixed") for r in s["rows"]]
    ptrrtti=[]
    for r in s["rows"]:
        if r["arr"]:
            for x in r["arr"]["ptrs"]:
                if x["rtti"]:
                    ptrrtti.append(x["rtti"])
    uniq_fixed=len({tuple(f or []) for f in fixed})
    if uniq_fixed>1 or ptrrtti or off in (96,512,904,928):
        out["arrays_interesting"].append({
            "off":off,
            "sizes":sizes,
            "fixed":fixed,
            "u32":[(r["arr"] or {}).get("u32") for r in s["rows"]],
            "rtti":sorted(set(ptrrtti)),
        })

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
# stdout compact
show={
    "hits": {k:v for k,v in hits.items() if v},
    "bat_arrays":[{"off":x["off"],"match":x["match"],"example":x["rows"][0]} for x in bat_offs],
    "officers":[{"id":o["id"],"expected":o["expected"],"leader_field":o["leader_field"],"name0":o.get("name_plus0"),"name8":o.get("name_plus8"),"name16":o.get("name_plus16"),"name24":o.get("name_plus24"),"strs":o.get("strs")} for o in officers],
    "carmy_ptr_summary":{str(off): {
        "self": sum(1 for r in rows if r.get("is_self")),
        "other_eth": [r.get("other_eth_id") or r.get("other_handle") for r in rows],
        "tags": [r.get("other_tag") for r in rows],
        "rtti": sorted({r.get("rtti") for r in rows if r.get("rtti")}),
    } for off,rows in carmy_ptrs.items()},
    "formation_country": formation["country_array_classes"],
    "formation_theatre": formation["theatres"],
    "characters": {"n":cm_info.get("n_chars"),"active":cm_info.get("n_active"),"hits":cm_info.get("hits")},
    "arrays_interesting":[{"off":a["off"],"sizes":a["sizes"],"fixed":a["fixed"],"rtti":a["rtti"]} for a in out["arrays_interesting"]],
}
print(json.dumps(show, ensure_ascii=False, indent=2))
p.close()
