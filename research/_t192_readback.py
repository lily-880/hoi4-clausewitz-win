from __future__ import annotations
import json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"calling"))
from pe import PE
from mem import Proc, find_pid as mem_find_pid
from gamestate import detect_session, resolve_player_country, _rtti_name_from_vtable, read_campaign_summary

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
GROUP = 0x26d2b077020
MEMBER0 = 0x26c9bbfb220
LEADER = 0x26cb4c76af0
MEMBER_UNIT = 1838
KEEP_UNIT = 1829

def is_ptr(x):
    return type(x) is int and 0x10000 < x < 0x7FFFFFFFFFFF

def msvc_string(p, a):
    blob = p.read(a, 32)
    n, cap = struct.unpack_from("<QQ", blob, 16)
    if not 0 <= n <= 1024 or cap < n:
        return None
    raw = blob[:n] if cap <= 15 else p.read(struct.unpack_from("<Q", blob)[0], n)
    return raw.decode("utf-8", "replace")

def pdx(p, a):
    data, cap, size = struct.unpack("<QII", p.read(a, 16))
    return {"data": hex(data) if is_ptr(data) else data, "raw_data": data, "cap": cap, "size": size}

def ptr_array(p, a, bound=4096):
    h = pdx(p, a)
    size = h["size"]
    data = h["raw_data"]
    if not 0 <= size <= h["cap"] <= max(bound, 100):
        return [], h
    if size and not is_ptr(data):
        return [], h
    return [struct.unpack("<Q", p.read(data + 8*j, 8))[0] for j in range(size)], h

def cls(p, pe, a):
    if not is_ptr(a):
        return None
    vt = struct.unpack("<Q", p.read(a, 8))[0]
    if not p.base <= vt < p.base + p.image_size:
        return None
    return _rtti_name_from_vtable(pe, vt - p.base)

def hexdump(p, a, n):
    b = p.read(a, n)
    lines = []
    for i in range(0, n, 16):
        chunk = b[i:i+16]
        hx = " ".join(f"{x:02x}" for x in chunk)
        q = []
        for j in range(0, len(chunk), 8):
            if j+8 <= len(chunk):
                q.append(hex(struct.unpack_from("<Q", chunk, j)[0]))
        lines.append(f"+{i:03x}: {hx}  {q}")
    return lines

p = Proc(mem_find_pid("hoi4.exe"))
pe = PE(EXE)
session = detect_session(p, pe)
gs = int(session["signals"]["gs_ptr"], 16)
co = int(resolve_player_country(p, gs)["country_ptr"], 16)
out = {"group": hex(GROUP), "member0": hex(MEMBER0), "leader": hex(LEADER)}

# dump group members area and identity
out["group_class"] = cls(p, pe, GROUP)
out["group_handle"] = struct.unpack("<II", p.read(GROUP+0x8, 8))
out["group_name"] = msvc_string(p, GROUP+0x160)
out["group_leader_88"] = hex(struct.unpack("<Q", p.read(GROUP+0x88, 8))[0])
mems, mh = ptr_array(p, GROUP+0x50, 256)
out["members_hdr"] = mh
out["members"] = []
for mp in mems:
    rec = {"ptr": hex(mp), "class": cls(p, pe, mp)}
    if is_ptr(mp):
        rec["u32"] = {hex(off): struct.unpack("<I", p.read(mp+off, 4))[0] for off in (0x8,0xc,0x10,0x14,0x18,0x1c,0x20,0x24,0x28,0x2c)}
        rec["name_try"] = {hex(off): msvc_string(p, mp+off) for off in (0x30,0x38,0x40,0x48,0x50,0x58,0x60,0x150,0x160,0x168)}
        rec["hex_00_80"] = hexdump(p, mp, 0x80)
    out["members"].append(rec)

# compare to unit 1838 and all own units
arr, ah = ptr_array(p, co+0x290, 4096)
out["own_unit_count"] = len(arr)
units = []
for ap in arr:
    uid = struct.unpack("<I", p.read(ap+0x1C, 4))[0]
    rec = {
        "ptr": hex(ap),
        "id": uid,
        "handle": struct.unpack("<II", p.read(ap+0x18, 8)),
        "prov": struct.unpack("<I", p.read(ap+0x28, 4))[0],
        "is_1838": uid==1838,
        "is_member0": ap==MEMBER0,
        "class": cls(p, pe, ap),
    }
    units.append(rec)
out["unit_1838"] = next((u for u in units if u["id"]==1838), None)
out["unit_1829"] = next((u for u in units if u["id"]==1829), None)
out["member0_in_own_units"] = any(int(u["ptr"],16)==MEMBER0 for u in units)
out["new_units_not_1829_1849"] = [u for u in units if not (1829<=u["id"]<=1849)]
out["own_units_all"] = units

# scan unit 1838 (and all units) for group pointer or handle (53,1)
u1838 = next((int(u["ptr"],16) for u in units if u["id"]==1838), 0)
scan = {"group_ptr_hits": [], "handle_53_1_hits": [], "handle_53_any": []}
for u in units:
    ap = int(u["ptr"], 16)
    blob = p.read(ap, 0x800)
    for off in range(0, 0x800-7, 8):
        q = struct.unpack_from("<Q", blob, off)[0]
        if q == GROUP:
            scan["group_ptr_hits"].append({"unit": u["id"], "off": hex(off)})
    for off in range(0, 0x800-7, 4):
        t, i = struct.unpack_from("<II", blob, off)
        if t == 53 and i == 1:
            scan["handle_53_1_hits"].append({"unit": u["id"], "off": hex(off)})
        elif t == 53:
            scan["handle_53_any"].append({"unit": u["id"], "off": hex(off), "id": i})
out["unit_scans"] = scan

# also scan a wider window 0x800-0xC00 if needed later

# leader 312 official assignment fields
out["leader_class"] = cls(p, pe, LEADER)
out["leader_handle"] = struct.unpack("<II", p.read(LEADER+0x8, 8))
out["leader_name_20"] = msvc_string(p, LEADER+0x20)
# known slots
for off in (0x1040,0x1048,0x1050,0x1058,0x1060,0x1068,0x1070,0x1078,0x1080):
    raw = p.read(LEADER+off, 16)
    out.setdefault("leader_known", {})[hex(off)] = {
        "u64": [hex(struct.unpack_from("<Q", raw, 0)[0]), hex(struct.unpack_from("<Q", raw, 8)[0])],
        "u32": list(struct.unpack_from("<IIII", raw)),
        "u8_1068_if": p.read(LEADER+0x1068, 1)[0] if off==0x1068 else None,
    }
out["leader_1068"] = p.read(LEADER+0x1068, 1)[0]
# scan leader object for group ptr and handle 53,1  — leader is large (~0x1100+)
leader_hits = {"group_ptr": [], "handle_53_1": [], "handle_53_any": [], "unit_1838_ptr": [], "handle_51_1838": []}
u1838p = u1838
blob = p.read(LEADER, 0x1200)
for off in range(0, 0x1200-7, 8):
    q = struct.unpack_from("<Q", blob, off)[0]
    if q == GROUP:
        leader_hits["group_ptr"].append(hex(off))
    if q == u1838p:
        leader_hits["unit_1838_ptr"].append(hex(off))
for off in range(0, 0x1200-7, 4):
    t, i = struct.unpack_from("<II", blob, off)
    if t == 53 and i == 1:
        leader_hits["handle_53_1"].append(hex(off))
    elif t == 53:
        leader_hits["handle_53_any"].append({"off": hex(off), "id": i})
    elif t == 0x33 and i == 1838:
        leader_hits["handle_51_1838"].append(hex(off))
out["leader_scans"] = leader_hits
out["leader_dump_1040"] = hexdump(p, LEADER+0x1040, 0x80)

# character backlink? CArmyLeader might be at character+0xa8
# also check CCharacter if leader has a parent

# theatre unit list still includes 1838?
theatres, _ = ptr_array(p, co+0x168, 64)
tp = theatres[0]
tunits, _ = ptr_array(p, tp+0x68, 4096)
out["theatre_unit_ids"] = [struct.unpack("<I", p.read(u+0x1C,4))[0] for u in tunits if is_ptr(u)]
out["theatre_has_1838"] = 1838 in out["theatre_unit_ids"]

# session still same
idler = int(session["signals"].get("idler_ptr") or "0", 16)
summary = read_campaign_summary(p, gs)
ver = summary.get("verified") or {}
out["session"] = {
    "pid": p.pid,
    "date": ver.get("date_full") or ver.get("date"),
    "pause": p.read(idler+0x6C1,1)[0],
    "speed": struct.unpack("<i", p.read(gs+0x4BC,4))[0],
}

Path("research/t192_readback.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str)+"\n", encoding="utf-8")
# compact print
print(json.dumps({
    "session": out["session"],
    "group_handle": out["group_handle"],
    "group_name": out["group_name"],
    "group_leader_88": out["group_leader_88"],
    "members": [{k:v for k,v in m.items() if k!="hex_00_80"} | {"hex_head": (m.get("hex_00_80") or [])[:6]} for m in out["members"]],
    "own_unit_count": out["own_unit_count"],
    "member0_in_own_units": out["member0_in_own_units"],
    "new_units": out["new_units_not_1829_1849"],
    "unit_1838": out["unit_1838"],
    "unit_scans": out["unit_scans"],
    "leader_handle": out["leader_handle"],
    "leader_1068": out["leader_1068"],
    "leader_scans": out["leader_scans"],
    "leader_known": out["leader_known"],
    "theatre_has_1838": out["theatre_has_1838"],
}, indent=2, ensure_ascii=False, default=str))
p.close()
