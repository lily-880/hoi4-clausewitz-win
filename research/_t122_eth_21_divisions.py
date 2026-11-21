import json, os, struct, sys, collections
sys.path.insert(0, os.path.join(os.getcwd(), "calling"))
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"

import config, offsets as O
from gamestate import _pdx_array
from handle import HANDLE_TYPE_ARMY, HANDLE_TYPE_TABLE, resolve_handle
from mem import Proc, find_pid

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
player = struct.unpack_from("<i", p.try_read(gs + O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"], 4), 0)[0]
cptr = struct.unpack_from("<Q", p.try_read(countries["data"] + player * 8, 8) or b"\0"*8, 0)[0]

CA_HANDLE = 0x18
CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_PROVINCE = 0x1F0
CA_DIV_TEMPLATE = 0x3B8
CP_ID = 0xA4
TMPL_NAME = 0x20

OOB = [
    {"name": "Kebur Zabagna", "template": "Kebur Zabagna", "province": 5010, "place": "Addis Ababa"},
    {"name": "1 Gojjam Provincial Sefari", "template": "Mehal Sefari", "province": 1984, "place": "Gondar"},
    {"name": "1 Wolqayt Provincial Sefari", "template": "Mountain Division", "province": 13237, "place": "Aksum"},
    {"name": "1 Semien Provincial Sefari", "template": "Mountain Division", "province": 13237, "place": "Aksum"},
    {"name": "1 Amino Provincial Sefari", "template": "Mehal Sefari", "province": 13238, "place": "Adwa area"},
    {"name": "1 Gubba Provincial Sefari", "template": "Mehal Sefari", "province": 13238, "place": "Adwa area"},
    {"name": "1 Gurage Provincial Sefari", "template": "Mehal Sefari", "province": 2072, "place": "Macalle"},
    {"name": "1 Jimma Provincial Sefari", "template": "Mehal Sefari", "province": 5097, "place": "Dessie"},
    {"name": "1 Om Hajer Provincial Sefari", "template": "Mehal Sefari", "province": 5097, "place": "Dessie"},
    {"name": "1 Sela Provincial Sefari", "template": "Mehal Sefari", "province": 7980, "place": None},
    {"name": "1 Welega Provincial Sefari", "template": "Mehal Sefari", "province": 5097, "place": "Dessie"},
    {"name": "1 Begemder Sefari", "template": "Chitet Sefari", "province": 2072, "place": "Macalle", "officer": "Wondosson Kassa"},
    {"name": "1 Tigray Sefari", "template": "Chitet Sefari", "province": 13238, "place": "Adwa"},
    {"name": "1 Wag Sefari", "template": "Chitet Sefari", "province": 7944, "place": None, "officer": "Haile Kebbede"},
    {"name": "1 Welega-Ardjo Sefari", "template": "Chitet Sefari", "province": 7944, "place": None, "officer": "Makonnen Demissie"},
    {"name": "1 Kaffa Sefari", "template": "Chitet Sefari", "province": 1984, "place": "Gondar", "officer": "Getachew Abate"},
    {"name": "1 Ogaden Sefari", "template": "Chitet Sefari", "province": 12812, "place": "Wal Wal", "officer": "Afawarq Walda Samayat"},
    {"name": "1 Hararghe Sefari", "template": "Chitet Sefari", "province": 12757, "place": None},
    {"name": "1 Illubabor Sefari", "template": "Chitet Sefari", "province": 4995, "place": None},
    {"name": "1 Bale Sefari", "template": "Chitet Sefari", "province": 4995, "place": None},
    {"name": "1 Sidamo Sefari", "template": "Chitet Sefari", "province": 8062, "place": None},
]
assert len(OOB) == 21

def u32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<I", b, 0)[0] if b else None

def u64(addr):
    b = p.try_read(addr, 8)
    return struct.unpack_from("<Q", b, 0)[0] if b else None

def looks_ptr(v):
    return isinstance(v, int) and 0x10000 < v < 0x7FFFFFFFFFFF

def read_utf8(addr, n=96):
    b = p.try_read(addr, n)
    if not b:
        return None
    s = b.split(b"\0", 1)[0]
    if not s or not all(32 <= x < 127 or x >= 128 for x in s[:1]):
        # still try decode
        pass
    try:
        t = s.decode("utf-8")
    except Exception:
        t = s.decode("utf-8", "replace")
    if t and t.isprintable():
        return t
    return t if t else None

def read_name(tmpl_ptr):
    if not tmpl_ptr:
        return None
    # proven: CReferencedDivisionTemplate+0x20 -> UTF-8 name
    raw = p.try_read(tmpl_ptr + TMPL_NAME, 16)
    if not raw:
        return None
    ptr = struct.unpack_from("<Q", raw, 0)[0]
    if looks_ptr(ptr):
        s = read_utf8(ptr)
        if s and any(c.isalpha() for c in s):
            return s
    # inline / SSO
    s = read_utf8(tmpl_ptr + TMPL_NAME)
    if s and any(c.isalpha() for c in s):
        return s
    return None

def describe(obj):
    if not obj:
        return None
    vt = u64(obj)
    vt_rva = (vt - p.base) if vt and p.base <= vt < p.base + p.image_size else None
    h_ty, h_ix = u32(obj + CA_HANDLE), u32(obj + CA_HANDLE + 4)
    prov_id = u32(obj + CA_PROVINCE_ID)
    tag = u32(obj + CA_COUNTRY_TAG)
    pref = u64(obj + CA_PROVINCE)
    pid_a4 = u32(pref + CP_ID) if pref else None
    tptr = u64(obj + CA_DIV_TEMPLATE)
    return {
        "ptr": hex(obj),
        "vt_rva": hex(vt_rva) if vt_rva is not None else None,
        "handle_type": h_ty,
        "handle_index": h_ix,
        "province_id": prov_id,
        "province_id_via_cprovince": pid_a4,
        "province_id_ok": pid_a4 == prov_id,
        "country_tag": tag,
        "template_ptr": hex(tptr) if tptr else None,
        "template_name": read_name(tptr),
    }

# country templates
tmpl_arr = _pdx_array(p, cptr + 0x1B8)
templates = []
if tmpl_arr:
    for i in range(tmpl_arr["size"]):
        tp = u64(tmpl_arr["data"] + i * 8)
        templates.append({"i": i, "ptr": hex(tp) if tp else None, "name": read_name(tp), "vt_rva": hex((u64(tp) - p.base) if tp and u64(tp) and p.base <= u64(tp) < p.base + p.image_size else 0) if tp else None})

# CO_ARMIES
army_arr = _pdx_array(p, cptr + 0x290)
co_ptrs = []
co_rows = []
for i in range(army_arr["size"]):
    obj = u64(army_arr["data"] + i * 8)
    co_ptrs.append(obj)
    rec = describe(obj) or {"ptr": hex(obj) if obj else None}
    rec["co_index"] = i
    rec["in_co_armies"] = True
    co_rows.append(rec)

# Walk handle type table for ARMY
reg = u64(p.base + HANDLE_TYPE_TABLE + HANDLE_TYPE_ARMY * 8)
reg_blob = p.try_read(reg, 0x40) if reg else None
reg_words = {}
if reg_blob and len(reg_blob) >= 0x20:
    for off in range(0, 0x40, 8):
        if off + 8 <= len(reg_blob):
            reg_words[hex(off)] = hex(struct.unpack_from("<Q", reg_blob, off)[0])
buckets = u64(reg + 8) if reg else None
mask = u32(reg + 0x14) if reg else None

handle_objs = []
seen = set()
walk_stats = {"buckets": 0, "empty": 0, "entries": 0, "errors": 0}
if buckets and mask is not None and mask < 1_000_000:
    walk_stats["buckets"] = mask + 1
    for h in range(mask + 1):
        slot = buckets + h * 24
        first = p.try_read(slot, 24)
        if not first:
            walk_stats["errors"] += 1
            continue
        # empty if +4 is 0
        if first[4] == 0:
            walk_stats["empty"] += 1
            continue
        # walk consecutive 24-byte nodes; stop at 128 or unreadable
        rax = slot
        for cl in range(1, 129):
            raw = p.try_read(rax, 24)
            if not raw or len(raw) < 24:
                break
            typ = struct.unpack_from("<I", raw, 8)[0]
            idx = struct.unpack_from("<I", raw, 0xC)[0]
            op = struct.unpack_from("<Q", raw, 0x10)[0]
            if typ == HANDLE_TYPE_ARMY and op:
                obj = op - 0x10
                if obj not in seen:
                    seen.add(obj)
                    handle_objs.append(obj)
                    walk_stats["entries"] += 1
            rax += 0x18
            nxt = p.try_read(rax, 5)
            if not nxt:
                break
            # reconstructed stop: cl > next[+4]
            if cl + 1 > nxt[4]:
                break

# Backup: resolve_handle over a wide index window if walk looks short
backup = []
if len(handle_objs) < 50:
    for ix in range(1, 20001):
        try:
            obj = resolve_handle(p, HANDLE_TYPE_ARMY, ix, p.base)
        except Exception:
            continue
        if obj and obj not in seen:
            seen.add(obj)
            backup.append(obj)
            handle_objs.append(obj)

# Describe all handle armies, group by country
by_tag = collections.Counter()
player_rows = []
for obj in handle_objs:
    rec = describe(obj)
    if not rec:
        continue
    tag = rec.get("country_tag")
    if tag is not None:
        by_tag[tag] += 1
    rec["in_co_armies"] = obj in set(co_ptrs)
    if tag == player:
        player_rows.append(rec)

# Also include any CO_ARMIES not found in handle walk
co_set = set(co_ptrs)
found_ptrs = set(int(r["ptr"], 16) for r in player_rows if r.get("ptr"))
for rec in co_rows:
    ptr = int(rec["ptr"], 16) if rec.get("ptr") else 0
    if ptr and ptr not in found_ptrs:
        rec["source"] = "co_armies_only"
        player_rows.append(rec)

# Match to OOB (multiset of template+province)
oob_left = [dict(x, matched=False) for x in OOB]
matches = []
unmatched_live = []
for rec in sorted(player_rows, key=lambda r: (r.get("province_id") or 0, r.get("template_name") or "", r.get("handle_index") or 0)):
    tname = rec.get("template_name")
    pid = rec.get("province_id")
    hit = None
    for o in oob_left:
        if o["matched"]:
            continue
        if pid == o["province"] and tname == o["template"]:
            hit = o
            break
    if hit:
        hit["matched"] = True
        matches.append({
            "oob_name": hit["name"],
            "template": tname,
            "province": pid,
            "place": hit.get("place"),
            "officer": hit.get("officer"),
            "in_co_armies": rec.get("in_co_armies"),
            "handle_index": rec.get("handle_index"),
            "ptr": rec.get("ptr"),
        })
    else:
        unmatched_live.append(rec)

missing_oob = [o for o in oob_left if not o["matched"]]

out = {
    "pid": p.pid,
    "player_index": player,
    "country_ptr": hex(cptr),
    "templates": templates,
    "co_armies_count": len(co_rows),
    "handle_walk": {"reg": hex(reg) if reg else None, "reg_words": reg_words, "mask": mask, "stats": walk_stats, "backup_added": len(backup)},
    "handle_armies_total": len(handle_objs),
    "armies_by_country_tag": dict(sorted(by_tag.items(), key=lambda kv: -kv[1])),
    "player_army_count": len(player_rows),
    "player_in_co_armies": sum(1 for r in player_rows if r.get("in_co_armies")),
    "player_not_in_co_armies": [r for r in player_rows if not r.get("in_co_armies")],
    "player_armies": player_rows,
    "matched": matches,
    "matched_count": len(matches),
    "missing_from_oob": missing_oob,
    "unmatched_live": unmatched_live,
}
path = os.path.join("research", "_t122_eth_21_divisions.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps({
    "templates": templates,
    "co_armies_count": out["co_armies_count"],
    "handle_walk_stats": walk_stats,
    "backup_added": len(backup),
    "handle_armies_total": len(handle_objs),
    "player_army_count": out["player_army_count"],
    "armies_by_country_tag_top": list(out["armies_by_country_tag"].items())[:8],
    "matched_count": out["matched_count"],
    "matched": matches,
    "missing_from_oob": missing_oob,
    "unmatched_live_brief": [
        {k: r.get(k) for k in ("ptr", "handle_index", "province_id", "template_name", "in_co_armies", "country_tag")}
        for r in unmatched_live
    ],
    "co_sample": [
        {k: r.get(k) for k in ("co_index", "handle_index", "province_id", "province_id_ok", "template_name", "country_tag", "vt_rva")}
        for r in co_rows[:5]
    ],
}, ensure_ascii=False, indent=2))
