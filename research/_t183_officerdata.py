import sys, struct, json, os, collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

p=Proc(find_pid("hoi4.exe"))
pe=PE(p.image_path)
try:
    def isptr(x):
        return type(x) is int and 0x10000 < x < 0x7fffffffffff
    def cls(a):
        if not isptr(a): return None
        vt=p.ptr(a)
        if not vt or not (p.base <= vt < p.base+p.image_size): return None
        try:
            n=_rtti_name_from_vtable(pe, vt-p.base)
            return n if n and n.startswith((".?AV",".?AU")) and n.endswith("@@") else None
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)

    ar=_pdx_array(p, co+0x290)
    officers=[]
    for slot in range(ar["size"]):
        ap=p.ptr(ar["data"]+slot*8)
        uid=p.u32(ap+0x1c)
        lid=p.i32(ap+0x564)
        op=p.ptr(ap+0x568)
        raw=p.try_read(op, 0x180) or b""
        rec={"unit_id":uid,"leader_id":lid,"op":hex(op or 0),"class":cls(op),"i32":{},"ptrs":[],"strings":{}}
        for off in range(0, min(len(raw)-3, 0x170), 4):
            rec["i32"][hex(off)]=struct.unpack_from("<i", raw, off)[0]
        # only keep interesting i32: not 0, or equals lid
        rec["i32_nz"]={k:v for k,v in rec["i32"].items() if v not in (0,1,-1) or (lid>=0 and v==lid)}
        for off in range(0, min(len(raw)-7, 0x170), 8):
            pv=struct.unpack_from("<Q", raw, off)[0]
            if isptr(pv):
                rec["ptrs"].append({"off":hex(off),"ptr":hex(pv),"class":cls(pv)})
        for off in (0x08,0x10,0x18,0x20,0x28,0x30,0x38,0x40,0x48):
            s=p.msvc_string(op+off) if op else None
            if s: rec["strings"][hex(off)]=s
        officers.append(rec)

    # compare assigned vs not: which offsets differ
    assigned=[o for o in officers if o["leader_id"]>=0]
    unassigned=[o for o in officers if o["leader_id"]<0]
    keys=set()
    for o in officers:
        keys |= set(o["i32"])
    diffs=[]
    for k in sorted(keys, key=lambda x:int(x,16)):
        av=set(o["i32"][k] for o in assigned)
        uv=set(o["i32"][k] for o in unassigned)
        if av != uv:
            diffs.append({"off":k,"assigned":list(av),"unassigned_sample":list(uv)[:6],"unassigned_nunique":len(uv)})

    print("n assigned", len(assigned), "unassigned", len(unassigned))
    print("DIFF i32", json.dumps(diffs, indent=2))
    print("assigned ptrs/strings")
    for o in assigned:
        print(json.dumps({k:o[k] for k in ("unit_id","leader_id","op","class","i32_nz","ptrs","strings")}, ensure_ascii=False))
    print("unassigned0", json.dumps({k:unassigned[0][k] for k in ("unit_id","leader_id","op","class","i32_nz","ptrs","strings")}, ensure_ascii=False))

    # GS manager scan for Character
    gs_managers=[]
    raw=p.try_read(gs, 0x900) or b""
    for off in range(8, min(len(raw)-7, 0x8f8), 8):
        v=struct.unpack_from("<Q", raw, off)[0]
        c=cls(v) if isptr(v) else None
        if c and any(s in c for s in ("Character","Leader","Theatre","Combat","Command","Manager","Group","Army")):
            gs_managers.append({"off":hex(off),"ptr":hex(v),"class":c})
    print("gs managers", json.dumps(gs_managers, ensure_ascii=False))

    out={"pid":p.pid,"assigned":assigned,"unassigned_count":len(unassigned),"unassigned_sample":unassigned[:2],"i32_diffs":diffs,"gs_managers":gs_managers,"country":hex(co),"gs":hex(gs)}
    Path("research/t183_live_officerdata.json").write_text(json.dumps(out, indent=2, default=str, ensure_ascii=False)+"\n", encoding="utf-8")
finally:
    p.close()
