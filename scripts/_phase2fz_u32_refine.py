#!/usr/bin/env python3
"""2fz refine: treat +0xe0/+0x100 as u32 streams (size*4), cross vs +0x70."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from config import allow_post
from process import Backend
from handle import resolve_handle
assert allow_post() is False
TYPE_OG=0x35; INST_VT=0x2A02558; CP_VT=0x29EE248; CP_ID=0xA4
b=Backend(); base=b.image_base
def u64(a): return struct.unpack("<Q", b.read(a,8))[0]
def u32(a): return struct.unpack("<I", b.read(a,4))[0]
def try_read(a,n):
    try: return b.read(a,n)
    except Exception: return None
def cpdx(addr):
    raw=try_read(addr,0x18)
    if not raw: return None
    data,cap,size=struct.unpack_from("<Qii", raw,0)
    ok=data>0x10000 and 0<=size<=8192 and size<=max(cap,size)
    sent=base<=data<base+b.image_size
    return dict(data=data,cap=cap,size=size,ok=ok,sent=sent)
def looks(v): return 1<=v<=20000
def u32_stream(arr):
    if not arr or not arr["ok"] or arr["size"]<=0 or arr["sent"]: return []
    n=min(arr["size"],256)
    blob=try_read(arr["data"], n*4)
    if not blob: return []
    return [struct.unpack_from("<I",blob,i*4)[0] for i in range(n)]
def ptr_stream(arr):
    if not arr or not arr["ok"] or arr["size"]<=0 or arr["sent"]: return []
    n=min(arr["size"],64)
    blob=try_read(arr["data"], n*8)
    if not blob: return []
    return [struct.unpack_from("<Q",blob,i*8)[0] for i in range(n)]
rows=[]
for oi in [4,5,6,7,8,9,13,17,20,22,25,27,38,40,44,52,68,70,124]:
    hdr=resolve_handle(b, TYPE_OG, oi, base)
    if not hdr: continue
    og=hdr+0x10
    a98=cpdx(og+0x98)
    if not a98 or not a98["ok"] or a98["size"]<1 or a98["sent"]: continue
    inst=u64(a98["data"])
    if u64(inst)-base != INST_VT: continue
    a70,a88,ae0,a100=(cpdx(inst+o) for o in (0x70,0x88,0xE0,0x100))
    s70=u32_stream(a70); se0=u32_stream(ae0); s100=u32_stream(a100)
    e0_all=bool(se0) and all(looks(v) for v in se0)
    e100_all=bool(s100) and all(looks(v) for v in s100)
    cp100=[]
    for p in ptr_stream(a100)[:32]:
        if p<0x10000: continue
        try:
            if u64(p)-base==CP_VT: cp100.append(u32(p+CP_ID))
        except Exception: pass
    # hub/neigh from 88
    hubs=[]; neigh=[]
    if a88 and a88["ok"] and a88["size"]>0 and not a88["sent"]:
        ids=[]
        for p in ptr_stream(a88)[:64]:
            if p<0x10000: ids.append(None); continue
            try:
                if u64(p)-base!=CP_VT: ids.append(None); continue
                ids.append(u32(p+CP_ID))
            except Exception: ids.append(None)
        for i in range(0,len(ids)-1,2):
            if ids[i] is not None: hubs.append(ids[i])
            if ids[i+1] is not None: neigh.append(ids[i+1])
    set70=set(s70); set_e0=set(se0); set_e100=set(s100)
    rows.append({
        "oi":oi,
        "n70":len(s70),"n88":(a88 or {}).get("size"),
        "n_e0":(ae0 or {}).get("size"),"n_100":(a100 or {}).get("size"),
        "e0_u32_all_prov":e0_all,"e100_u32_all_prov":e100_all,
        "se0":se0,"s100":s100,"s70":s70,
        "hubs":hubs,"neigh":neigh,
        "e0_eq_70": se0==s70 and bool(se0),
        "e100_eq_70": s100==s70 and bool(s100),
        "e0_eq_e100": se0==s100 and bool(se0),
        "e0_subset_70": set_e0<=set70 and bool(set_e0),
        "e100_subset_70": set_e100<=set70 and bool(set_e100),
        "overlap_e0_70": sorted(set_e0 & set70),
        "overlap_e100_70": sorted(set_e100 & set70),
        "overlap_e0_hubs": sorted(set_e0 & set(hubs)),
        "overlap_e0_neigh": sorted(set_e0 & set(neigh)),
        "cp100":cp100,
        "e0_cap":(ae0 or {}).get("cap"),"e100_cap":(a100 or {}).get("cap"),
        # packed-pair consistency: reading size qwords as consecutive u32 pairs equals se0 if size*2 u32s?
        "note_stride": "u32_stream uses size*4 bytes = size u32s",
    })
non=[r for r in rows if (r["n_e0"] or 0)>0 or (r["n_100"] or 0)>0]
agg={
    "nonempty":len(non),
    "e0_all_prov":sum(1 for r in non if r["e0_u32_all_prov"]),
    "e100_all_prov":sum(1 for r in non if r["e100_u32_all_prov"]),
    "e0_eq_e100":sum(1 for r in non if r["e0_eq_e100"]),
    "e0_eq_70":sum(1 for r in non if r["e0_eq_70"]),
    "e0_subset_70":sum(1 for r in non if r["e0_subset_70"]),
    "any_overlap_e0_70":sum(1 for r in non if r["overlap_e0_70"]),
    "any_overlap_e0_hubs":sum(1 for r in non if r["overlap_e0_hubs"]),
    "size_e0_eq_e100_all":all((r.get("n_e0")==r.get("n_100")) for r in rows if r.get("n_e0") is not None),
    "cp100_any":sum(1 for r in non if r["cp100"]),
}
print(json.dumps({"agg":agg,"samples":[{k:r[k] for k in ("oi","n70","n88","n_e0","n_100","e0_u32_all_prov","e100_u32_all_prov","e0_eq_e100","e0_eq_70","e0_subset_70","se0","s100","s70","overlap_e0_70","overlap_e0_hubs","cp100")} for r in non]}, indent=2))
(ROOT/"reports"/"_phase2fz_u32_refine.json").write_text(json.dumps({"agg":agg,"rows":rows}, indent=2), encoding="utf-8")
