#!/usr/bin/env python3
"""Dump unknown cmd vtables seen on postexec/pending during brief 1x poll. RO."""
from __future__ import annotations
import json, os, struct, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))
KNOWN = {0x2A2C790,0x2A2C9B8,0x2A2D818,0x2A85468,0x2A27F28,0x2A5F448,0x2A1F648,0x2A83ED8,0x2A84498,0x2A843E0,0x2A83D68,0x2A84C80,0x2A84B10,0x2A84DF0,0x2A84550,0x2A85520}
from mem import Proc, find_pid
p = Proc(find_pid("hoi4.exe"))
ov = json.load(open(os.path.join(ROOT,"calling","offsets_verified.json"),encoding="utf-8"))
idler = p.u64(p.base + ov["G_IDLER"]); session = p.u64(p.u64(idler+0x530)+0x380); server = p.u64(session+0x40)
unk = {}
for i in range(800):
    for head_off, label in ((0x58,"pending"),(0x40,"execlist")):
        node = p.u64(server + head_off)
        seen=set()
        while node and node not in seen:
            seen.add(node)
            try:
                cmd=p.u64(node); nxt=p.u64(node+0x10); vt=p.u64(cmd)-p.base
            except OSError: break
            if vt not in KNOWN:
                unk[hex(vt)] = unk.get(hex(vt),0)+1
            node=nxt
    # stage array
    sc=p.u32(session+0x54); data=p.u64(session+0x48)
    for j in range(min(sc,64)):
        try:
            cmd=p.u64(data+j*8); vt=p.u64(cmd)-p.base
            if vt not in KNOWN: unk[hex(vt)] = unk.get(hex(vt),0)+1
        except OSError: break
    # ring slots rough: server+0xa0 looks like concurrent ring object — try +0/+8 heads if ptrlike
    time.sleep(0.015)
# also try RTTI name for top unknown
from gamestate import _rtti_name_from_vtable
named={}
for vt_hex,c in sorted(unk.items(), key=lambda x:-x[1])[:20]:
    vt=int(vt_hex,16)
    try:
        nm=_rtti_name_from_vtable(p, p.base+vt)
    except Exception as e:
        nm=str(e)
    named[vt_hex]={"count":c,"rtti":nm}
out={"phase":"2ap-unknown-vt","posting":"DISABLED","unknown_vt":named,"exec":p.u32(session+0x6c8),"seq":p.u32(server+0xd0)}
path=os.path.join(ROOT,"research","re-dumps","phase2ap_unknown_vt.json")
json.dump(out,open(path,"w",encoding="utf-8"),indent=2)
print(json.dumps(out,indent=2)[:3000])
p.close()
