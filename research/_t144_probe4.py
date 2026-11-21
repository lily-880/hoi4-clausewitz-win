import os, sys, json, struct, math
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import _pdx_array, resolve_player_country, _rtti_name_from_vtable
from pe import PE

OUT = Path("research/_t144_probe4.json")
FIXED = 100000
CA_HANDLE = 0x18
CARMY_SZ = 0x690

EXPECTED = {
    1829: dict(name="Kebur Zabagna", eq=1.0, xp=0.2, officer=None, mp=5000, max_org=62.0, hp=125.0, bat=5, prov=5010, tmpl="Kebur Zabagna"),
    1830: dict(name="1 Gojjam Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=1984, tmpl="Mehal Sefari"),
    1831: dict(name="1 Wolqayt Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=70.0, hp=80.0, bat=4, prov=13237, tmpl="Mountain Division"),
    1832: dict(name="1 Semien Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=70.0, hp=80.0, bat=4, prov=13237, tmpl="Mountain Division"),
    1833: dict(name="1 Amino Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=13238, tmpl="Mehal Sefari"),
    1834: dict(name="1 Gubba Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=13238, tmpl="Mehal Sefari"),
    1835: dict(name="1 Gurage Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=2072, tmpl="Mehal Sefari"),
    1836: dict(name="1 Jimma Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=5097, tmpl="Mehal Sefari"),
    1837: dict(name="1 Om Hajer Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=5097, tmpl="Mehal Sefari"),
    1838: dict(name="1 Sela Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=7980, tmpl="Mehal Sefari"),
    1839: dict(name="1 Welega Yekilili Sefari", eq=0.8, xp=0.2, officer=None, mp=4000, max_org=60.0, hp=100.0, bat=4, prov=5097, tmpl="Mehal Sefari"),
    1840: dict(name="1 Begemder Sefari", eq=0.6, xp=0.05, officer="Wondosson Kassa", mp=6000, max_org=45.0, hp=180.0, bat=6, prov=2072, tmpl="Chitet Sefari"),
    1841: dict(name="1 Tigray Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, hp=180.0, bat=6, prov=13238, tmpl="Chitet Sefari"),
    1842: dict(name="1 Wag Sefari", eq=0.45, xp=0.05, officer="Haile Kebbede", mp=6000, max_org=45.0, hp=180.0, bat=6, prov=7944, tmpl="Chitet Sefari"),
    1843: dict(name="1 Welega-Ardjo Sefari", eq=1.0, xp=0.25, officer="Makonnen Demissie", mp=6000, max_org=45.0, hp=180.0, bat=6, prov=7944, tmpl="Chitet Sefari"),
    1844: dict(name="1 Kaffa Sefari", eq=0.6, xp=0.05, officer="Getachew Abate", mp=6000, max_org=45.0, hp=180.0, bat=6, prov=1984, tmpl="Chitet Sefari"),
    1845: dict(name="1 Ogaden Sefari", eq=0.6, xp=0.05, officer="Afawarq Walda Samayat", mp=6000, max_org=45.0, hp=180.0, bat=6, prov=12812, tmpl="Chitet Sefari"),
    1846: dict(name="1 Hararghe Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, hp=180.0, bat=6, prov=12757, tmpl="Chitet Sefari"),
    1847: dict(name="1 Illubabor Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, hp=180.0, bat=6, prov=4995, tmpl="Chitet Sefari"),
    1848: dict(name="1 Bale Sefari", eq=0.6, xp=0.05, officer=None, mp=6000, max_org=45.0, hp=180.0, bat=6, prov=4995, tmpl="Chitet Sefari"),
    1849: dict(name="1 Sidamo Sefari", eq=0.9, xp=0.2, officer=None, mp=6000, max_org=45.0, hp=180.0, bat=6, prov=8062, tmpl="Chitet Sefari"),
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
        return name[4:-2]
    return name
def class_of(addr):
    return rtti_name(u64(addr)) if looks_ptr(addr) else None
def pdx_array(addr):
    data, cap, size = u64(addr), u32(addr+8), u32(addr+12)
    if not looks_ptr(data) or cap is None or size is None:
        return None
    if cap > 8000 or size > cap:
        return None
    return {"data": data, "cap": cap, "size": size}

def raw_name(addr):
    # Try MSVC string with exact size, then raw 16-byte inline, then pointer
    blob = p.try_read(addr, 32) or b""
    rec = {"hex": blob[:32].hex()}
    size = u32(addr+16)
    cap = u32(addr+24)
    ptr = u64(addr)
    rec["size"]=size; rec["cap"]=cap; rec["ptr"]=hex(ptr) if ptr else None
    def dec(b, n=None):
        if n is not None:
            b=b[:n]
        try:
            return b.split(b"\0",1)[0].decode("utf-8")
        except Exception:
            try:
                return b[:n].decode("utf-8", "replace") if n else None
            except Exception:
                return None
    if size is not None and 0 < size < 80:
        if cap is not None and cap >= 16 and looks_ptr(ptr):
            raw=p.try_read(ptr, size+1) or b""
            rec["name"]=dec(raw, size)
            rec["how"]="heap"
        else:
            rec["name"]=dec(blob, size)
            rec["how"]="inline"
    elif looks_ptr(ptr):
        raw=p.try_read(ptr, 80) or b""
        rec["name"]=dec(raw)
        rec["how"]="ptr_nosize"
    else:
        rec["name"]=dec(blob, 16)
        rec["how"]="inline16"
    return rec

resolved = resolve_player_country(p, gs)
idx = resolved["player_index"]
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
cptr = u64(countries["data"] + idx * 8)
armies = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_ARMIES"])
units=[]
for slot in range(armies["size"]):
    ap = u64(armies["data"] + slot * 8)
    if not ap: continue
    uid = u32(ap + CA_HANDLE + 4)
    units.append({"id": uid, "ptr": ap, "exp": EXPECTED[uid]})

# verify org/hp
verify=[]
for u in units:
    org = i32(u["ptr"]+0x428)/FIXED
    hp  = i32(u["ptr"]+0x420)/FIXED
    eq1 = i32(u["ptr"]+0x468)/FIXED
    eq2 = i32(u["ptr"]+0x5A8)/FIXED
    xp  = i32(u["ptr"]+0x5B8)/FIXED
    e=u["exp"]
    verify.append({
        "id":u["id"], "org":round(org,5), "org_ok": abs(org-e["max_org"]*0.95)<1e-6,
        "hp":round(hp,5), "hp_ok": abs(hp-e["hp"])<1e-6,
        "eq1":eq1, "eq2":eq2, "eq_ok": abs(eq1-e["eq"])<1e-9 and abs(eq2-e["eq"])<1e-9,
        "xp":xp, "xp_ok": abs(xp-e["xp"])<1e-9,
        "name":e["name"], "tmpl":e["tmpl"]
    })

# dump 0x400-0x47C and 0x5A0-0x5D0 as constants too
def block(off0, off1):
    out=[]
    for off in range(off0, off1, 4):
        xs=[None if i32(u["ptr"]+off) is None else round(i32(u["ptr"]+off)/FIXED,5) for u in units]
        ivs=[i32(u["ptr"]+off) for u in units]
        uniq=sorted(set(xs))
        out.append({"off":hex(off), "nuniq":len(set(xs)), "uniq":uniq[:12], "xs":xs, "sample_i":ivs[0]})
    return out

# manpower targets
mp_targets = {
    "max": [u["exp"]["mp"] for u in units],
    "eq_scaled": [int(round(u["exp"]["mp"]*u["exp"]["eq"])) for u in units],
    "thousands": [u["exp"]["mp"]/1000.0 for u in units],
    "thousands_eq": [u["exp"]["mp"]/1000.0*u["exp"]["eq"] for u in units],
    "max_fixed": [u["exp"]["mp"]*FIXED for u in units],  # as raw i32 if stored strangely
}

mp_hits=[]
# search CArmy 0..0x68C, and each CSubUnitDefinition 0..0x400
for off in range(0, CARMY_SZ-3, 4):
    ivs=[i32(u["ptr"]+off) for u in units]
    fxs=[None if v is None else v/FIXED for v in ivs]
    fvs=[f32(u["ptr"]+off) for u in units]
    for label, target in mp_targets.items():
        def close(vals, tgt, tol):
            if any(v is None for v in vals): return 0
            return sum(abs(a-b)<=tol for a,b in zip(vals,tgt))
        n=close(ivs, target, 0)
        if n>=18 and label in ("max","eq_scaled"):
            mp_hits.append({"where":"CArmy","off":off,"src":"i32","kind":label,"n":n,"vals":ivs})
        n=close(fxs, target, 0.02)
        if n>=18 and label in ("max","eq_scaled","thousands","thousands_eq"):
            mp_hits.append({"where":"CArmy","off":off,"src":"fixed","kind":label,"n":n,"vals":[round(v,4) for v in fxs]})
        n=close(fvs, target, 0.02)
        if n>=18:
            mp_hits.append({"where":"CArmy","off":off,"src":"f32","kind":label,"n":n,"vals":[None if v is None else round(v,4) for v in fvs]})

# also search def
for u in units:
    u["def"]=u64(u["ptr"]+0x138)

# compare defs
for off in range(0, 0x800-3, 4):
    ivs=[i32(u["def"]+off) for u in units]
    fxs=[None if v is None else v/FIXED for v in ivs]
    for label, target in [("max", mp_targets["max"]), ("eq_scaled", mp_targets["eq_scaled"]),
                          ("thousands", mp_targets["thousands"]), ("thousands_eq", mp_targets["thousands_eq"])]:
        n=sum(a is not None and abs(a-b)<= (0 if label in ("max","eq_scaled") and False else 0.02 if "thousand" in label or True and label.startswith("t") else 0) for a,b in zip((ivs if label in ("max","eq_scaled") else fxs), target))
        # redo clearly
    n_max=sum(a==b for a,b in zip(ivs, mp_targets["max"]))
    n_eqs=sum(a==b for a,b in zip(ivs, mp_targets["eq_scaled"]))
    n_th=sum(a is not None and abs(a-b)<=0.02 for a,b in zip(fxs, mp_targets["thousands"]))
    n_te=sum(a is not None and abs(a-b)<=0.02 for a,b in zip(fxs, mp_targets["thousands_eq"]))
    if n_max>=18: mp_hits.append({"where":"def","off":off,"src":"i32","kind":"max","n":n_max,"vals":ivs})
    if n_eqs>=18: mp_hits.append({"where":"def","off":off,"src":"i32","kind":"eq_scaled","n":n_eqs,"vals":ivs})
    if n_th>=18: mp_hits.append({"where":"def","off":off,"src":"fixed","kind":"thousands","n":n_th,"vals":[round(v,4) for v in fxs]})
    if n_te>=18: mp_hits.append({"where":"def","off":off,"src":"fixed","kind":"thousands_eq","n":n_te,"vals":[round(v,4) for v in fxs]})

# 1.0 fields (possible current/max strength ratio, in_supply)
ones=[]
for off in range(0, CARMY_SZ-3, 4):
    fxs=[None if i32(u["ptr"]+off) is None else i32(u["ptr"]+off)/FIXED for u in units]
    if all(v is not None and abs(v-1.0)<1e-9 for v in fxs):
        ones.append(off)

# fields that vary by province more than template
by_prov={}
for u in units:
    by_prov.setdefault(u["exp"]["prov"], []).append(u)
prov_fields=[]
for off in range(0, CARMY_SZ-3, 4):
    # skip pointers
    ivs=[i32(u["ptr"]+off) for u in units]
    if any(v is None for v in ivs): continue
    if all(abs(v)>0x10000 and abs(v)<0x7FFFFFFF for v in ivs):
        continue  # likely not small stats; still allow fixed 0-2
    fxs=[v/FIXED for v in ivs]
    if not all(-1 <= v <= 100 for v in fxs):
        continue
    # same province should share value, different templates in same prov can differ if template-based
    # we want: value groups better by province than by template
    from collections import defaultdict
    pv=defaultdict(set); tv=defaultdict(set)
    for u,v in zip(units,fxs):
        pv[u["exp"]["prov"]].add(round(v,5))
        tv[u["exp"]["tmpl"]].add(round(v,5))
    # if any province has multiple values, not a pure province field
    # if templates have multiple values AND provinces are internally consistent, interesting
    prov_consistent=all(len(s)==1 for s in pv.values())
    tmpl_inconsistent=any(len(s)>1 for s in tv.values())
    nuniq=len(set(round(v,5) for v in fxs))
    if prov_consistent and tmpl_inconsistent and nuniq>=2:
        prov_fields.append({"off":hex(off),"nuniq":nuniq,"by_prov":{str(k):list(s)[0] for k,s in pv.items()},
                            "xs":[round(v,5) for v in fxs]})

# officer names
officers=[]
for u in units:
    op=u64(u["ptr"]+0x568)
    oid=i32(u["ptr"]+0x564)
    rec={"id":u["id"],"expected":u["exp"]["officer"],"leader_id":oid,"obj":hex(op) if looks_ptr(op) else None}
    if looks_ptr(op):
        rec["at0"]=raw_name(op)
        rec["at10"]=raw_name(op+0x10)
        rec["at18"]=raw_name(op+0x18)
        rec["bytes10"]=(p.try_read(op+0x10, 48) or b"").hex()
    officers.append(rec)

# equipment array at 0x3A0 and 0x388
eq_arrays=[]
for u in units[:]:
    rec={"id":u["id"],"eq":u["exp"]["eq"],"bat":u["exp"]["bat"]}
    for name,off in (("388",0x388),("3A0",0x3A0),("350",0x350),("368",0x368)):
        arr=pdx_array(u["ptr"]+off)
        if not arr:
            rec[name]=None
            continue
        raw=p.try_read(arr["data"], arr["size"]*8) or b""
        elems=[]
        for i in range(arr["size"]):
            if (i+1)*4<=len(raw):
                iv=struct.unpack_from("<i", raw, i*4)[0]
                pv=struct.unpack_from("<Q", raw, i*8)[0] if (i+1)*8<=len(raw) else 0
                e={"i":iv,"x":round(iv/FIXED,5)}
                if looks_ptr(pv):
                    e["ptr"]=hex(pv); e["rtti"]=class_of(pv)
                elems.append(e)
        rec[name]={"size":arr["size"],"cap":arr["cap"],"elems":elems}
    eq_arrays.append(rec)

# path still empty?
paths=[{"id":u["id"],"path":pdx_array(u["ptr"]+0x200)} for u in units]

# GS combats
comb=_pdx_array(p, gs+O.HYPOTHESIS_STRUCT["GS_COMBATS"]) if "GS_COMBATS" in O.HYPOTHESIS_STRUCT else None
# try known offset 0x268
if comb is None:
    try:
        comb=_pdx_array(p, gs+0x268)
    except Exception:
        comb=None

out={
    "verify": verify,
    "verify_all_org": all(v["org_ok"] for v in verify),
    "verify_all_hp": all(v["hp_ok"] for v in verify),
    "verify_all_eq": all(v["eq_ok"] for v in verify),
    "verify_all_xp": all(v["xp_ok"] for v in verify),
    "block_400": block(0x400, 0x480),
    "block_5a0": block(0x590, 0x5E0),
    "mp_hits": mp_hits,
    "ones_offs": [hex(o) for o in ones],
    "prov_fields": prov_fields,
    "officers": officers,
    "eq_arrays": eq_arrays,
    "paths": paths,
    "combats": comb,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
show={
    "verify_all": {k: out[k] for k in ("verify_all_org","verify_all_hp","verify_all_eq","verify_all_xp")},
    "org_hp": [{"id":v["id"],"org":v["org"],"hp":v["hp"],"ok":v["org_ok"] and v["hp_ok"]} for v in verify],
    "mp_hits": mp_hits,
    "ones": out["ones_offs"],
    "prov_fields": prov_fields,
    "officers": [{"id":o["id"],"exp":o["expected"],"lid":o["leader_id"],
                  "n0": (o.get("at0") or {}).get("name"), "h0": (o.get("at0") or {}).get("how"),
                  "n10": (o.get("at10") or {}).get("name"), "h10": (o.get("at10") or {}).get("how"),
                  "size10": (o.get("at10") or {}).get("size"), "cap10": (o.get("at10") or {}).get("cap")} for o in officers if o["expected"] or o["leader_id"]!=-1],
    "eq_arrays": eq_arrays[:3]+eq_arrays[11:15],
    "path_sizes": [((p["path"] or {}).get("size") if p["path"] else None) for p in paths],
    "combats": comb,
    "const_400": [b for b in out["block_400"] if b["nuniq"]<=6],
}
print(json.dumps(show, ensure_ascii=False, indent=2))
p.close()
