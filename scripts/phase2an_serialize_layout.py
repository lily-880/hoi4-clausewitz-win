"""Phase 2an — CUnitMoveAction serialize field layout (RO); posting DISABLED."""
from __future__ import annotations
import argparse, json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "calling"))
ACTION_FIELDS = [
    {"off": 0x10, "token": 0x28A3, "name": "unit", "kind": "handle", "writer": 0x2285670},
    {"off": 0x18, "token": 0x2840, "name": "province", "kind": "pdxarray", "size_off": 0x24, "writer": 0x1D2BF0},
    {"off": 0x30, "token": 0x174, "name": "path", "kind": "pdxarray", "size_off": 0x3C, "writer": 0x1D2BF0},
    {"off": 0x50, "token": 0x29F1, "name": "clear", "kind": "bool"},
    {"off": 0x51, "token": 0x2C84, "name": "safe", "kind": "bool"},
    {"off": 0x53, "token": 0x38F1, "name": "safe_with_nonsafe_fallback", "kind": "bool"},
    {"off": 0x52, "token": 0x3A98, "name": "safe_until_very_end", "kind": "bool"},
    {"off": 0x55, "token": 0x2C85, "name": "avoid", "kind": "bool"},
    {"off": 0x58, "token": 0x37BC, "name": "move_priority", "kind": "enum_i32", "default_skip": 1, "enum_fn": 0x19D7560},
    {"off": 0x5C, "token": 0x368F, "name": "sticky", "kind": "bool"},
]
MOVE_CMD_ACTION = 0x28
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--live", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "research", "re-dumps", "phase2an_report.json"))
    args = ap.parse_args()
    layout = []
    for f in ACTION_FIELDS:
        e = dict(f); e["cmd_off"] = MOVE_CMD_ACTION + f["off"]; e["token_hex"] = hex(f["token"]); e["off_hex"] = hex(f["off"]); layout.append(e)
    out = {"phase":"2an","posting":"DISABLED","command_queue":"DISABLED","speed_rule":"pause or 1x only; never 5x",
           "CUnitMoveAction_SERIALIZE":hex(0x12C3920),"CUnitMoveAction_DESERIALIZE":hex(0x12C3340),
           "CMoveCommand_ACTION_EMBED":hex(MOVE_CMD_ACTION),"action_fields":layout,
           "notes":["province/path only if size>0","bools only if nonzero","move_priority skip if ==1","+0x54 unused","safe-enable NOT proven"]}
    if args.live:
        from process import Backend, find_pid
        b = Backend(find_pid("hoi4.exe")); base = b.image_base
        checks = {"unit_lea":(0x12C393D,b"\x48\x8d\x53\x10"),"prov_lea":(0x12C394F,b"\x4c\x8d\x43\x18"),
                  "path_lea":(0x12C3966,b"\x4c\x8d\x43\x30"),"clear_ld":(0x12C3977,b"\x44\x0f\xb6\x43\x50"),
                  "prio_ld":(0x12C39EA,b"\x8b\x53\x58"),"sticky_ld":(0x12C3A0C,b"\x44\x0f\xb6\x43\x5c")}
        verified = {n:{"rva":hex(r),"ok":b.read(base+r,len(e))==e,"got":b.read(base+r,len(e)).hex()} for n,(r,e) in checks.items()}
        out["live_byte_checks"]=verified; out["all_checks_ok"]=all(v["ok"] for v in verified.values())
        vt=base+0x2A1F648; pat=__import__("struct").pack("<Q",vt); hits=0
        maps=b.maps
        for m in maps:
            if not isinstance(m, dict): continue
            perms=str(m.get("perms") or m.get("protection") or "")
            if "w" not in perms.lower() and "WRITE" not in perms: continue
            start=m.get("start") or m.get("base") or m.get("addr"); size=m.get("size") or m.get("region_size")
            if start is None or size is None or size>0x20000000: continue
            try: blob=b.read(start,size)
            except Exception: continue
            off=0
            while True:
                i=blob.find(pat,off)
                if i<0: break
                if i%8==0: hits+=1
                off=i+8
                if hits>50: break
            if hits>50: break
        out["heap_CUnitMoveAction_vt_hits"]=hits; b.close()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out,"w",encoding="utf-8"), indent=2)
    print("wrote", args.out)
    for e in layout: print(f"  action+{e['off_hex']} cmd+{hex(e['cmd_off'])} {e['name']} ({e['kind']}) token {e['token_hex']}")
    if args.live: print("checks", out["all_checks_ok"]); print("heap_hits", out.get("heap_CUnitMoveAction_vt_hits"))
if __name__ == "__main__": main()
