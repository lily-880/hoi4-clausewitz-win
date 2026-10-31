#!/usr/bin/env python3
"""2fw addendum: Instance+0x88 CProvince* → id@+0xA4 vs +0x70 u32s (RO)."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "calling"))
from config import allow_post
from process import Backend
from handle import resolve_handle
assert allow_post() is False
TYPE_OG=0x35
CP_ID=0xA4
CP_VT=0x29EE248

def u64(b,a): return struct.unpack("<Q", b.read(a,8))[0]
def u32(b,a): return struct.unpack("<I", b.read(a,4))[0]
def try_read(b,a,n):
    try: return b.read(a,n)
    except Exception: return None

def read_cpdx(b, base, addr):
    raw=try_read(b,addr,0x18)
    if not raw: return None
    data,cap,size=struct.unpack_from("<Qii", raw, 0)
    plausible=data>0x10000 and 0<=size<=4096 and size<=cap
    return {"data":data,"size":size,"cap":cap,"plausible":plausible,
            "sentinel": base<=data<base+b.image_size}

def main():
    b=Backend(); base=b.image_base
    prev=json.loads((ROOT/"reports"/"phase2fw_prov70_crosscheck.json").read_text(encoding="utf-8"))
    out=[]
    for row in prev["rows"]:
        if not row.get("ok"): continue
        oi=row["order_index"]
        link=row.get("link") or {}
        # re-resolve inst
        hdr=resolve_handle(b, TYPE_OG, oi, base)
        if not hdr: continue
        og=hdr+0x10
        a98=read_cpdx(b, base, og+0x98)
        if not a98 or not a98["plausible"] or a98["size"]<1: continue
        inst=u64(b, a98["data"])
        a70=read_cpdx(b, base, inst+0x70)
        a88=read_cpdx(b, base, inst+0x88)
        u32s=[]
        if a70 and a70["plausible"] and a70["size"]>0 and not a70["sentinel"]:
            blob=try_read(b, a70["data"], min(a70["size"],64)*4)
            if blob: u32s=[struct.unpack_from("<I",blob,i*4)[0] for i in range(min(a70["size"],64))]
        ids88=[]; vtok=0; ptrs=[]
        if a88 and a88["plausible"] and a88["size"]>0 and not a88["sentinel"]:
            n=min(a88["size"],32)
            blob=try_read(b, a88["data"], n*8)
            if blob:
                for i in range(n):
                    p=struct.unpack_from("<Q",blob,i*8)[0]
                    ptrs.append(hex(p))
                    if p<0x10000: continue
                    try:
                        vt=u64(b,p)-base
                        if vt==CP_VT: vtok+=1
                        pid=u32(b,p+CP_ID)
                        ids88.append(pid)
                    except Exception:
                        ids88.append(None)
        set70=set(u32s); set88=set(x for x in ids88 if x is not None)
        out.append({
            "oi": oi,
            "n70": len(u32s), "n88": (a88 or {}).get("size"),
            "vt_ok_88": vtok,
            "ids88": ids88,
            "u32s70": u32s,
            "overlap_70_88": sorted(set70 & set88),
            "frac_70_in_88": (len(set70 & set88)/len(set70)) if set70 else None,
            "frac_88_in_70": (len(set70 & set88)/len(set88)) if set88 else None,
            "equal_as_sets": set70==set88 and bool(set70),
            "army_provs": row.get("army_province_ids"),
            "overlap_88_vs_army": sorted(set88 & set(row.get("army_province_ids") or [])),
        })
    print(json.dumps(out, indent=2))
    (ROOT/"reports"/"phase2fw_88_vs_70.json").write_text(json.dumps({"allow_post":False,"rows":out}, indent=2), encoding="utf-8")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
