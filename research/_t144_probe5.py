import os, sys, json, struct, math
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import _pdx_array, resolve_player_country, _rtti_name_from_vtable
from pe import PE

OUT = Path("research/_t144_probe5.json")
FIXED = 100000
CA_HANDLE = 0x18

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
def read_utf8(addr, n=80):
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
    prov_id = u32(ap + 0x28)
    ratio40 = i32(ap + 0x40)/FIXED
    prov = u64(ap + 0x1F0)
    units.append({"id": uid, "ptr": ap, "prov_id": prov_id, "r40": ratio40, "prov": prov})

# unique provinces
provs={}
for u in units:
    provs.setdefault(u["prov_id"], {"ptr": u["prov"], "r40": u["r40"], "units": []})
    provs[u["prov_id"]]["units"].append(u["id"])

# For each unique CProvince, find fields equal to r40, and list rtti ptrs / 0-1 fixed
prov_scan=[]
for pid, info in sorted(provs.items()):
    addr=info["ptr"]
    rec={"prov_id": pid, "ptr": hex(addr) if addr else None, "rtti": class_of(addr), "r40": info["r40"], "units": info["units"], "matches": [], "ptrs": [], "ones": []}
    if not looks_ptr(addr):
        prov_scan.append(rec); continue
    blob=p.try_read(addr, 0x200) or b""
    target=info["r40"]
    for off in range(0, len(blob)-3, 4):
        iv=struct.unpack_from("<i", blob, off)[0]
        fx=iv/FIXED
        if abs(fx - target) < 1e-5:
            rec["matches"].append({"off": off, "i": iv, "x": round(fx,5)})
        if abs(fx-1.0)<1e-9 or (0 <= fx <= 1.0001 and abs(fx-0)>1e-9 and abs(fx-target)>1e-4):
            rec["ones"].append({"off": off, "x": round(fx,5)})
    for off in range(0, len(blob)-7, 8):
        pv=struct.unpack_from("<Q", blob, off)[0]
        if looks_ptr(pv):
            nm=class_of(pv)
            if nm:
                rec["ptrs"].append({"off": off, "rtti": nm, "ptr": hex(pv)})
    # also id field
    rec["id_at_A4"]=u32(addr+0xA4)
    prov_scan.append(rec)

# officer names: dump 0x40 bytes and try first-char recovery
# also search nearby heap for expected full names
EXPECTED_OFF={1840:"Wondosson Kassa",1842:"Haile Kebbede",1843:"Makonnen Demissie",1844:"Getachew Abate",1845:"Afawarq Walda Samayat"}
officers=[]
for u in units:
    op=u64(u["ptr"]+0x568)
    oid=i32(u["ptr"]+0x564)
    if oid==-1 and not looks_ptr(op):
        continue
    rec={"id":u["id"],"leader_id":oid,"obj":hex(op) if looks_ptr(op) else None,"rtti":class_of(op) if looks_ptr(op) else None}
    if looks_ptr(op):
        blob=p.try_read(op, 0x40) or b""
        rec["hex"]=blob.hex()
        # standard: maybe first char lives just before the 00... try all offsets
        names=[]
        for off in range(0, len(blob)):
            # take cstring
            s=blob[off:].split(b"\0",1)[0]
            try:
                t=s.decode("utf-8")
            except Exception:
                continue
            if t and t.isprintable() and any(c.isalpha() for c in t) and len(t)>=5:
                names.append({"off":off,"s":t})
        rec["cstrs"]=names
        # heap at +0x10 (skip maybe tag)
        for off in (0x10, 0x18, 0x08, 0x00):
            pv=u64(op+off)
            if looks_ptr(pv) and pv < 0x7F0000000000:
                s=read_utf8(pv, 64)
                if s:
                    rec.setdefault("heap", []).append({"off":off,"ptr":hex(pv),"s":s})
        # try reconstructing first letter: if bytes at 0x10 start with 00, prepend?? search process for expected
        exp=EXPECTED_OFF.get(u["id"])
        rec["expected"]=exp
        if exp:
            # search 1MB around officer and around subunit for the utf-8 name
            found=[]
            needle=exp.encode("utf-8")
            for base,label in ((op-0x100,"off-0x100"), (op, "off"), (u["ptr"], "army")):
                window=p.try_read(base, 0x400) or b""
                i=window.find(needle)
                if i>=0:
                    found.append({"where":label,"at":hex(base+i)})
            rec["needle"]=found
    officers.append(rec)

# manpower neighbors
mp_block=[]
for off in range(0x4E0, 0x520, 4):
    xs=[round(i32(u["ptr"]+off)/FIXED,5) for u in units]
    mp_block.append({"off":hex(off),"uniq":sorted(set(xs)),"xs":xs})

# 0x4A0 neighbors (the all-1.0 field)
r4a0=[]
for off in range(0x490, 0x4C0, 4):
    xs=[round(i32(u["ptr"]+off)/FIXED,5) for u in units]
    r4a0.append({"off":hex(off),"uniq":sorted(set(xs))})

# meta
hour = u32(gs + O.HYPOTHESIS_STRUCT.get("GS_DATE_HOUR_TICK", 0x468))
speed = i32(gs + 0x4BC)
prog = struct.unpack_from("<f", p.try_read(gs+0x4B8,4) or b"\0"*4, 0)[0]
pid = p.pid if hasattr(p,"pid") else None

out={
    "meta":{"pid":pid, "player_index":idx, "hour_tick":hour, "speed":speed, "hour_progress":prog,
            "resolved": resolved},
    "prov_scan": prov_scan,
    "officers": officers,
    "mp_block": mp_block,
    "r4a0": r4a0,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
show={
    "meta": out["meta"],
    "prov": [{"id":x["prov_id"],"r40":x["r40"],"rtti":x["rtti"],"idA4":x.get("id_at_A4"),
              "matches":x["matches"], "ptrs":x["ptrs"][:12],
              "ratio_like":[o for o in x["ones"] if 0<o["x"]<=1][:15]} for x in prov_scan],
    "officers":[{"id":o["id"],"lid":o["leader_id"],"cstrs":o.get("cstrs"),"heap":o.get("heap"),"needle":o.get("needle"),"expected":o.get("expected")} for o in officers],
    "mp_block": mp_block,
    "r4a0": r4a0,
}
print(json.dumps(show, ensure_ascii=False, indent=2))
p.close()
