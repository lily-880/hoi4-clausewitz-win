import os, sys, json, struct, math, collections
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import _pdx_array, resolve_player_country, _rtti_name_from_vtable
from pe import PE

OUT = Path("research/_t144_probe3.json")
FIXED = 100000
CA_HANDLE = 0x18
CARMY_SZ = 0x690

EXPECTED = {
    1829: dict(name="Kebur Zabagna", eq=1.0, xp=0.2, officer=None, mp=5000, max_org=62.0, bat=5),
    1830: dict(name="1 Gojjam Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1831: dict(name="1 Wolqayt Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=70.0, bat=4),
    1832: dict(name="1 Semien Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=70.0, bat=4),
    1833: dict(name="1 Amino Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1834: dict(name="1 Gubba Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1835: dict(name="1 Gurage Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1836: dict(name="1 Jimma Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1837: dict(name="1 Om Hajer Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1838: dict(name="1 Sela Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1839: dict(name="1 Welega Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, bat=4),
    1840: dict(name="1 Begemder Sefari", eq=0.6, xp=0.05, officer="Wondosson Kassa", mp=6000, max_org=45.0, bat=6),
    1841: dict(name="1 Tigray Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, bat=6),
    1842: dict(name="1 Wag Sefari", eq=0.45, xp=0.05, officer="Haile Kebbede", mp=6000, max_org=45.0, bat=6),
    1843: dict(name="1 Welega-Ardjo Sefari", eq=1.0, xp=0.25, officer="Makonnen Demissie", mp=6000, max_org=45.0, bat=6),
    1844: dict(name="1 Kaffa Sefari", eq=0.6, xp=0.05, officer="Getachew Abate", mp=6000, max_org=45.0, bat=6),
    1845: dict(name="1 Ogaden Sefari", eq=0.6, xp=0.05, officer="Afawarq Walda Samayat", mp=6000, max_org=45.0, bat=6),
    1846: dict(name="1 Hararghe Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, bat=6),
    1847: dict(name="1 Illubabor Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, bat=6),
    1848: dict(name="1 Bale Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, bat=6),
    1849: dict(name="1 Sidamo Sefari", eq=0.9, xp=0.2, officer=None, mp=6000, max_org=45.0, bat=6),
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
    if name and name.startswith(".?A") and name.endswith("@@"):
        # .?AV or .?AU
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

def msvc_string(addr):
    if not addr: return None
    size = u32(addr + 16)
    cap = u32(addr + 24)  # size_t, low 32
    # also try cap at +20 if 32-bit fields? MSVC x64: size at +16, cap at +24
    ptr = u64(addr)
    if cap is not None and size is not None and size < 200:
        if cap >= 16 and looks_ptr(ptr):
            return read_utf8(ptr, size+1)
        if cap < 16 or not looks_ptr(ptr):
            s = read_utf8(addr, min(size+1, 16) if size else 16)
            if s: return s
    if looks_ptr(ptr):
        s = read_utf8(ptr)
        if s: return s
    return read_utf8(addr, 16)

def pdx_array(addr):
    data, cap, size = u64(addr), u32(addr+8), u32(addr+12)
    if not looks_ptr(data) or cap is None or size is None:
        return None
    if cap > 8000 or size > cap:
        return None
    return {"data": data, "cap": cap, "size": size}

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

# allocation stride check
ptrs = sorted(u["ptr"] for u in units)
deltas = sorted({ptrs[i+1]-ptrs[i] for i in range(len(ptrs)-1) if 0 < ptrs[i+1]-ptrs[i] < 0x5000})

# officer names
officers=[]
for u in units:
    op=u64(u["ptr"]+0x568)
    oid=i32(u["ptr"]+0x564)
    rec={"id":u["id"],"expected":u["exp"]["officer"],"leader_id":oid,"has_obj":looks_ptr(op)}
    if looks_ptr(op):
        rec["obj"]=hex(op)
        rec["rtti"]=class_of(op)
        rec["name"]=msvc_string(op+0x10) or msvc_string(op) or msvc_string(op+0x8)
        rec["name_alts"]={hex(o): msvc_string(op+o) for o in (0,8,0x10,0x18,0x20)}
    officers.append(rec)

# stats block: for each 4-byte off in 0x400..0x68C, show values of all units as fixed if in range, else i32/f32 if interesting
def describe_off(off):
    rows=[]
    for u in units:
        iv=i32(u["ptr"]+off); fv=f32(u["ptr"]+off)
        fx = None if iv is None else iv/FIXED
        rows.append({"id":u["id"], "i":iv, "f": None if fv is None else round(fv,5), "x": None if fx is None else round(fx,5), "eq":u["exp"]["eq"], "org":u["exp"]["max_org"], "mp":u["exp"]["mp"]})
    return rows

interesting=[]
for off in range(0x400, CARMY_SZ-3, 4):
    rows=describe_off(off)
    ivs=[r["i"] for r in rows]
    fxs=[r["x"] for r in rows]
    fvs=[r["f"] for r in rows]
    # skip pointer-looking (all huge or all 0 with ptr at 8-align)
    uniq_fx=len(set(fxs))
    uniq_i=len(set(ivs))
    keep=False
    reason=""
    # fixed in -0.05..200 with variation or matching known
    if all(x is not None and -0.05 <= x <= 200 for x in fxs) and uniq_fx>=2:
        keep=True; reason="fixed_var"
    if all(v is not None and 0 <= v <= 20000 for v in ivs) and uniq_i>=2:
        keep=True; reason=reason or "i32_small_var"
    # exact known
    if fxs==[u["exp"]["eq"] for u in units] or fxs==[u["exp"]["xp"] for u in units]:
        keep=True; reason="exact_known"
    if keep:
        interesting.append({"off":off, "reason":reason, "values":[{"id":r["id"],"i":r["i"],"x":r["x"],"f":r["f"]} for r in rows]})

# CSubUnitDefinition dump
def dump_obj(addr, n=0x300):
    if not looks_ptr(addr):
        return None
    blob=p.try_read(addr, n) or b""
    rec={"ptr":hex(addr),"rtti":class_of(addr),"size_read":len(blob),"ptrs":[],"arrays":[],"fixed":[],"strs":[]}
    for off in range(0, len(blob)-7, 8):
        pv=struct.unpack_from("<Q", blob, off)[0]
        if looks_ptr(pv):
            nm=class_of(pv)
            if nm:
                rec["ptrs"].append({"off":off,"rtti":nm,"ptr":hex(pv)})
        arr=pdx_array(addr+off)
        if arr and arr["size"]>0:
            elems=[]
            raw=p.try_read(arr["data"], min(arr["size"],8)*8) or b""
            for i in range(min(arr["size"],8)):
                if (i+1)*8<=len(raw):
                    q=struct.unpack_from("<Q", raw, i*8)[0]
                    if looks_ptr(q):
                        elems.append({"rtti":class_of(q),"ptr":hex(q)})
                    else:
                        elems.append({"u32":struct.unpack_from("<I", raw, i*4)[0] if (i+1)*4<=len(raw) else None,
                                      "fixed": (struct.unpack_from("<I", raw, i*4)[0]/FIXED) if (i+1)*4<=len(raw) else None})
            rec["arrays"].append({"off":off,"size":arr["size"],"cap":arr["cap"],"elems":elems})
        s=msvc_string(addr+off)
        if s and len(s)>=3:
            rec["strs"].append({"off":off,"s":s})
    for off in range(0, len(blob)-3, 4):
        iv=struct.unpack_from("<i", blob, off)[0]
        if 0 < iv < 50*FIXED:
            fx=iv/FIXED
            if 0 <= fx <= 200 and (iv % 100==0 or 0.01<=fx<=100):
                rec["fixed"].append({"off":off,"i":iv,"x":round(fx,5)})
    # compact fixed: only unique-looking
    return rec

subunit_defs=[]
for u in units:
    dptr=u64(u["ptr"]+0x138)
    rec=dump_obj(dptr, 0x400)
    rec_s={"id":u["id"],"name":u["exp"]["name"],"eq":u["exp"]["eq"],"mp":u["exp"]["mp"],"org":u["exp"]["max_org"],"bat":u["exp"]["bat"],"def":rec}
    subunit_defs.append(rec_s)

# compare def objects: find offs whose fixed values track org/mp/eq/bat
def_hits={"org":[],"mp":[],"eq":[],"bat":[]}
# build per-off values from first 0x400
off_map=collections.defaultdict(list)
for rec_s in subunit_defs:
    rec=rec_s["def"]
    if not rec: continue
    # re-read raw for systematic compare
    addr=int(rec["ptr"],16)
    for off in range(0, 0x400-3, 4):
        iv=i32(addr+off); fv=f32(addr+off)
        off_map[off].append((rec_s["id"], iv, fv, None if iv is None else iv/FIXED, rec_s))

for off, rows in off_map.items():
    fxs=[r[3] for r in rows]
    ivs=[r[1] for r in rows]
    fvs=[r[2] for r in rows]
    orgs=[r[4]["org"] for r in rows]
    mps=[r[4]["mp"] for r in rows]
    eqs=[r[4]["eq"] for r in rows]
    bats=[r[4]["bat"] for r in rows]
    def score(vals, target, tol):
        if any(v is None for v in vals): return None
        n=sum(abs(a-b)<=tol for a,b in zip(vals,target))
        return n
    n=score(fxs, orgs, 0.6)
    if n and n>=18: def_hits["org"].append({"off":off,"src":"fixed","n":n,"values":[round(v,4) for v in fxs]})
    n=score(ivs, [int(o) for o in orgs], 0)
    if n and n>=18: def_hits["org"].append({"off":off,"src":"i32","n":n,"values":ivs})
    n=score(fvs, orgs, 0.6)
    if n and n>=18: def_hits["org"].append({"off":off,"src":"f32","n":n,"values":[None if v is None else round(v,4) for v in fvs]})
    n=score(ivs, mps, 0)
    if n and n>=18: def_hits["mp"].append({"off":off,"src":"i32","n":n,"values":ivs})
    n=score(fxs, mps, 1)
    if n and n>=18: def_hits["mp"].append({"off":off,"src":"fixed","n":n,"values":[round(v,4) for v in fxs]})
    n=score(fxs, eqs, 0.03)
    if n and n>=18: def_hits["eq"].append({"off":off,"src":"fixed","n":n,"values":[round(v,4) for v in fxs]})
    n=score(ivs, bats, 0)
    if n and n>=18: def_hits["bat"].append({"off":off,"src":"i32","n":n,"values":ivs})

# CFront membership
cptr_th = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_THEATRES"])
th=u64(cptr_th["data"]) if cptr_th and cptr_th.get("data") else 0
fronts=[]
if looks_ptr(th):
    arr=pdx_array(th+0x50)
    if arr:
        unit_ptr={u["ptr"]:u["id"] for u in units}
        for i in range(arr["size"]):
            fp=u64(arr["data"]+i*8)
            rec={"i":i,"ptr":hex(fp) if fp else None,"rtti":class_of(fp),"arrays":[],"unit_hits":[]}
            if looks_ptr(fp):
                blob=p.try_read(fp, 0x300) or b""
                # any our army ptr or handle
                for off in range(0, len(blob)-7, 8):
                    q=struct.unpack_from("<Q", blob, off)[0]
                    if q in unit_ptr:
                        rec["unit_hits"].append({"kind":"ptr","off":off,"id":unit_ptr[q]})
                    arr2=pdx_array(fp+off)
                    if arr2 and 0<arr2["size"]<=200:
                        ids=[]
                        raw=p.try_read(arr2["data"], arr2["size"]*8) or b""
                        for j in range(arr2["size"]):
                            if (j+1)*8<=len(raw):
                                pv=struct.unpack_from("<Q", raw, j*8)[0]
                                if pv in unit_ptr:
                                    ids.append(unit_ptr[pv])
                                elif looks_ptr(pv) and class_of(pv):
                                    ids.append(class_of(pv))
                            if (j+1)*8<=len(raw):
                                typ=struct.unpack_from("<I", raw, j*8)[0] if False else None
                        # also handles typ 0x33
                        for j in range(0, len(raw)-7, 8):
                            typ=struct.unpack_from("<I", raw, j)[0]
                            ix=struct.unpack_from("<I", raw, j+4)[0]
                            if typ==0x33 and ix in EXPECTED:
                                ids.append(ix)
                        rec["arrays"].append({"off":off,"size":arr2["size"],"cap":arr2["cap"],"ids_or_rtti":ids[:20], "elem0_rtti": class_of(struct.unpack_from("<Q", raw, 0)[0]) if len(raw)>=8 and looks_ptr(struct.unpack_from("<Q", raw, 0)[0]) else None})
                rec["name"]=msvc_string(fp+0x20) or msvc_string(fp+0x18) or msvc_string(fp+0x10) or msvc_string(fp)
            fronts.append(rec)

# neighbors of the two eq fields and xp
neighbors={}
for off in (0x460,0x468,0x470,0x5A0,0x5A8,0x5B0,0x5B8,0x5C0,0x5C8,0x5D0):
    neighbors[hex(off)] = [{"id":u["id"], "x": None if i32(u["ptr"]+off) is None else round(i32(u["ptr"]+off)/FIXED,5), "i": i32(u["ptr"]+off)} for u in units]

out={
    "stride_deltas": [hex(d) for d in deltas[:20]],
    "officers": officers,
    "stats_interesting": interesting,
    "def_hits": def_hits,
    "subunit_defs_compact": [
        {"id":s["id"], "def": s["def"]["ptr"] if s["def"] else None, "rtti": s["def"]["rtti"] if s["def"] else None,
         "ptrs": s["def"]["ptrs"] if s["def"] else None,
         "arrays": s["def"]["arrays"] if s["def"] else None,
         "strs": s["def"]["strs"] if s["def"] else None,
         "fixed_interesting": [f for f in (s["def"]["fixed"] if s["def"] else []) if 0.04 <= f["x"] <= 120][:40]}
        for s in subunit_defs
    ],
    "fronts": fronts,
    "neighbors": neighbors,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
show={
    "stride_deltas": out["stride_deltas"],
    "officers":[{"id":o["id"],"expected":o["expected"],"leader_id":o["leader_id"],"name":o.get("name"),"alts":o.get("name_alts")} for o in officers if o["expected"] or o.get("name")],
    "stats_offs":[{"off":hex(s["off"]),"reason":s["reason"],"xs":[v["x"] for v in s["values"]], "is":[v["i"] for v in s["values"]]} for s in interesting],
    "def_hits": def_hits,
    "def_sample": out["subunit_defs_compact"][0],
    "def_sample_chitet": out["subunit_defs_compact"][11],
    "fronts":[{"i":f["i"],"name":f.get("name"),"unit_hits":f["unit_hits"],"arrays":f["arrays"]} for f in fronts],
    "neighbors": neighbors,
}
print(json.dumps(show, ensure_ascii=False, indent=2))
p.close()
