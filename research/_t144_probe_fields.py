import os, sys, json, struct, math, collections
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import (
    _pdx_array, resolve_player_country, read_campaign_summary, _rtti_name_from_vtable
)
from country_tags import tag_for_index
from handle import resolve_handle, HANDLE_TYPE_ARMY
from pe import PE

OUT = Path("research/_t144_fields.json")
CA_HANDLE = 0x18
CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_SUBUNIT_DEF = 0x138
CA_PROVINCE = 0x1F0
CA_DIV_TEMPLATE = 0x3B8
CA_NAME_MEMBER = 0x340
CA_PATH = 0x200
CNG_DISPLAY_NAME = 0x60
CP_ID = 0xA4
TMPL_NAME = 0x20
DUMP = 0x800

EXPECTED = {
    1829: dict(name="Kebur Zabagna", tmpl="Kebur Zabagna", eq=1.0, xp=0.2, officer=None, loc=5010, mp=5000, max_org=62.0, width=10),
    1830: dict(name="1 Gojjam Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=1984, mp=4000, max_org=60.0, width=8),
    1831: dict(name="1 Wolqayt Yekilili Sefari", tmpl="Mountain Division", eq=0.8, xp=0.2, officer=None, loc=13237, mp=4000, max_org=70.0, width=8),
    1832: dict(name="1 Semien Yekilili Sefari", tmpl="Mountain Division", eq=0.8, xp=0.2, officer=None, loc=13237, mp=4000, max_org=70.0, width=8),
    1833: dict(name="1 Amino Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=13238, mp=4000, max_org=60.0, width=8),
    1834: dict(name="1 Gubba Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=13238, mp=4000, max_org=60.0, width=8),
    1835: dict(name="1 Gurage Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=2072, mp=4000, max_org=60.0, width=8),
    1836: dict(name="1 Jimma Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=5097, mp=4000, max_org=60.0, width=8),
    1837: dict(name="1 Om Hajer Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=5097, mp=4000, max_org=60.0, width=8),
    1838: dict(name="1 Sela Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=7980, mp=4000, max_org=60.0, width=8),
    1839: dict(name="1 Welega Yekilili Sefari", tmpl="Mehal Sefari", eq=0.8, xp=0.2, officer=None, loc=5097, mp=4000, max_org=60.0, width=8),
    1840: dict(name="1 Begemder Sefari", tmpl="Chitet Sefari", eq=0.6, xp=0.05, officer="Wondosson Kassa", loc=2072, mp=6000, max_org=45.0, width=12),
    1841: dict(name="1 Tigray Sefari", tmpl="Chitet Sefari", eq=0.6, xp=0.05, officer=None, loc=13238, mp=6000, max_org=45.0, width=12),
    1842: dict(name="1 Wag Sefari", tmpl="Chitet Sefari", eq=0.45, xp=0.05, officer="Haile Kebbede", loc=7944, mp=6000, max_org=45.0, width=12),
    1843: dict(name="1 Welega-Ardjo Sefari", tmpl="Chitet Sefari", eq=1.0, xp=0.25, officer="Makonnen Demissie", loc=7944, mp=6000, max_org=45.0, width=12),
    1844: dict(name="1 Kaffa Sefari", tmpl="Chitet Sefari", eq=0.6, xp=0.05, officer="Getachew Abate", loc=1984, mp=6000, max_org=45.0, width=12),
    1845: dict(name="1 Ogaden Sefari", tmpl="Chitet Sefari", eq=0.6, xp=0.05, officer="Afawarq Walda Samayat", loc=12812, mp=6000, max_org=45.0, width=12),
    1846: dict(name="1 Hararghe Sefari", tmpl="Chitet Sefari", eq=0.6, xp=0.05, officer=None, loc=12757, mp=6000, max_org=45.0, width=12),
    1847: dict(name="1 Illubabor Sefari", tmpl="Chitet Sefari", eq=0.6, xp=0.05, officer=None, loc=4995, mp=6000, max_org=45.0, width=12),
    1848: dict(name="1 Bale Sefari", tmpl="Chitet Sefari", eq=0.6, xp=0.05, officer=None, loc=4995, mp=6000, max_org=45.0, width=12),
    1849: dict(name="1 Sidamo Sefari", tmpl="Chitet Sefari", eq=0.9, xp=0.2, officer=None, loc=8062, mp=6000, max_org=45.0, width=12),
}

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
exe = getattr(p, "image_path", None) or r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(exe)

class Backend:
    def __init__(self, proc):
        self._p = proc
        self.image_base = proc.base
    def read(self, a, n):
        b = self._p.try_read(a, n)
        if not b or len(b) < n:
            raise OSError("short")
        return b
b = Backend(p)

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
    if not x:
        return None
    v = struct.unpack_from("<f", x, 0)[0]
    if not math.isfinite(v):
        return None
    return v
def looks_ptr(x):
    return bool(x) and 0x10000 < x < 0x7FFFFFFFFFFF
def rtti_name(vt):
    if not vt or vt < p.base:
        return None
    try:
        name = _rtti_name_from_vtable(pe, vt - p.base)
    except Exception:
        return None
    if name and name.startswith(".?AV") and name.endswith("@@"):
        return name[4:-2]
    return name
def class_of(addr):
    return rtti_name(u64(addr)) if looks_ptr(addr) else None
def read_utf8(addr, n=96):
    raw = p.try_read(addr, n)
    if not raw:
        return None
    s = raw.split(b"\0", 1)[0]
    if not s:
        return None
    try:
        t = s.decode("utf-8")
    except Exception:
        return None
    if not all(ch.isprintable() or ch in " \t" for ch in t):
        return None
    return t or None
def read_pdx_string(addr):
    if not addr:
        return None
    ptr = u64(addr)
    if looks_ptr(ptr):
        s = read_utf8(ptr)
        if s:
            return s
    return read_utf8(addr)
def maybe_array(addr):
    data, cap, size = u64(addr), u32(addr + 8), u32(addr + 12)
    if not looks_ptr(data) or cap is None or size is None:
        return None
    if cap > 4000 or size > cap or size > 2000:
        return None
    if cap == 0 and size == 0:
        return {"data": hex(data), "cap": cap, "size": size, "elems": []}
    return {"data": hex(data), "cap": cap, "size": size}

resolved = resolve_player_country(p, gs)
summary = read_campaign_summary(p, gs)
player_index = resolved.get("player_index")
player_tag = resolved.get("tag") or tag_for_index(player_index)
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
cptr = u64(countries["data"] + player_index * 8)
armies = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_ARMIES"])

units = []
for slot in range(armies["size"]):
    ap = u64(armies["data"] + slot * 8)
    if not ap:
        continue
    uid = u32(ap + CA_HANDLE + 4)
    blob = p.try_read(ap, DUMP) or b""
    units.append({"id": uid, "ptr": ap, "blob": blob, "exp": EXPECTED.get(uid, {})})

# floats / ints / ptrs per offset
float_rows = {}
int_rows = {}
ptr_rows = {}
array_rows = {}
ids = [u["id"] for u in units]
for off in range(0, DUMP - 3, 4):
    fvals, ivals = [], []
    okf = oki = 0
    for u in units:
        blob = u["blob"]
        if off + 4 > len(blob):
            fvals.append(None); ivals.append(None); continue
        fv = struct.unpack_from("<f", blob, off)[0]
        iv = struct.unpack_from("<i", blob, off)[0]
        if math.isfinite(fv):
            okf += 1
            fvals.append(fv)
        else:
            fvals.append(None)
        ivals.append(iv)
        oki += 1
    float_rows[off] = fvals
    int_rows[off] = ivals

for off in range(0, DUMP - 7, 8):
    pvals, rttis, arrs = [], [], []
    for u in units:
        blob = u["blob"]
        if off + 8 > len(blob):
            pvals.append(None); rttis.append(None); arrs.append(None); continue
        pv = struct.unpack_from("<Q", blob, off)[0]
        pvals.append(pv if looks_ptr(pv) else (0 if pv == 0 else pv))
        rttis.append(class_of(pv) if looks_ptr(pv) else None)
        arrs.append(maybe_array(u["ptr"] + off) if looks_ptr(pv) else None)
    ptr_rows[off] = {"ptrs": pvals, "rtti": rttis, "arrays": arrs}

def mae(xs, ys):
    diffs = [abs(a - b) for a, b in zip(xs, ys) if a is not None and b is not None]
    return sum(diffs) / len(diffs) if diffs else 999

def close_count(xs, ys, tol):
    n = 0
    tot = 0
    for a, b in zip(xs, ys):
        if a is None or b is None:
            continue
        tot += 1
        if abs(a - b) <= tol:
            n += 1
    return n, tot

eqs = [u["exp"].get("eq") for u in units]
xps = [u["exp"].get("xp") for u in units]
mps = [u["exp"].get("mp") for u in units]
orgs = [u["exp"].get("max_org") for u in units]
widths = [u["exp"].get("width") for u in units]
has_off = [1 if u["exp"].get("officer") else 0 for u in units]

eq_hits = []
xp_hits = []
org_hits = []
mp_hits = []
width_hits = []
for off, fvals in float_rows.items():
    if sum(v is not None for v in fvals) < 18:
        continue
    # skip obvious pointers interpreted as float
    if any((v is not None and abs(v) > 1e6) for v in fvals):
        # still allow int matches later
        pass
    n, tot = close_count(fvals, eqs, 0.03)
    if tot and n >= 18:
        eq_hits.append((off, n, tot, mae(fvals, eqs), [None if v is None else round(v, 5) for v in fvals]))
    n, tot = close_count(fvals, xps, 0.03)
    if tot and n >= 18:
        xp_hits.append((off, n, tot, mae(fvals, xps), [None if v is None else round(v, 5) for v in fvals]))
    n, tot = close_count(fvals, orgs, 0.6)
    if tot and n >= 18:
        org_hits.append((off, n, tot, mae(fvals, orgs), [None if v is None else round(v, 4) for v in fvals]))
    # also current org as fraction of max
    frac = [None if v is None or o is None or o == 0 else v / o for v, o in zip(fvals, orgs)]
    # and raw max-like values around 45-70
    # equipment as percent 45-100
    n, tot = close_count(fvals, [None if e is None else e * 100 for e in eqs], 2.0)
    if tot and n >= 18:
        eq_hits.append((off, n, tot, mae(fvals, [e*100 for e in eqs]), [None if v is None else round(v, 4) for v in fvals] + ["as_percent"]))

for off, ivals in int_rows.items():
    n, tot = close_count(ivals, mps, 0)
    if tot and n >= 16:
        mp_hits.append((off, n, tot, ivals))
    n, tot = close_count(ivals, widths, 0)
    if tot and n >= 18:
        width_hits.append((off, n, tot, ivals))
    # manpower maybe stored as current==max
    # also maybe 1000*battalions already in mps

# officer-discriminating pointers / ints
officer_fields = []
for off, info in ptr_rows.items():
    ptrs = info["ptrs"]
    rtti = info["rtti"]
    nz_off = [looks_ptr(pv) for pv, h in zip(ptrs, has_off) if h]
    z_no = [not looks_ptr(pv) for pv, h in zip(ptrs, has_off) if not h]
    if nz_off and z_no and all(nz_off) and all(z_no):
        officer_fields.append({
            "off": off, "kind": "ptr_exact",
            "rtti": sorted({r for r in rtti if r}),
            "values": [hex(pv) if looks_ptr(pv) else pv for pv in ptrs],
        })
    # weaker: all officer units share nonzero, some non-officer also nonzero - skip
for off, ivals in int_rows.items():
    if off % 8 == 0:
        continue  # overlap with ptrs more interesting first
    nz_off = [iv not in (0, None, -1) for iv, h in zip(ivals, has_off) if h]
    z_no = [iv in (0, None, -1) for iv, h in zip(ivals, has_off) if not h]
    if nz_off and z_no and all(nz_off) and all(z_no):
        officer_fields.append({"off": off, "kind": "i32_exact", "values": ivals})

# path arrays at +0x200 and any other u32 arrays of province-like values
path_like = []
for off, info in ptr_rows.items():
    arrs = info["arrays"]
    useful = [a for a in arrs if a and a.get("size", 0) >= 0]
    if not useful:
        continue
    # read elems if size>0
    samples = []
    for u, a in zip(units, arrs):
        if not a:
            samples.append(None)
            continue
        size = a["size"]
        if size == 0:
            samples.append([])
            continue
        data = int(a["data"], 16)
        elems = []
        # try u32 first
        raw = p.try_read(data, min(size, 32) * 4) or b""
        for i in range(min(size, 32)):
            if (i+1)*4 <= len(raw):
                elems.append(struct.unpack_from("<I", raw, i*4)[0])
        samples.append(elems)
        a["u32_head"] = elems[:12]
    nonempty = sum(1 for s in samples if s)
    if nonempty or off in (CA_PATH,):
        path_like.append({"off": off, "nonempty": nonempty, "rtti": sorted({r for r in info["rtti"] if r}), "samples": samples, "meta": arrs})

# unique pointer RTTI in CArmy
rtti_map = collections.defaultdict(list)
for off, info in ptr_rows.items():
    names = {r for r in info["rtti"] if r}
    for n in names:
        rtti_map[n].append(off)

# GS_COMBATS
combats_arr = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COMBATS"])
combat_info = {"size": None if not combats_arr else combats_arr.get("size"), "cap": None if not combats_arr else combats_arr.get("capacity"), "items": []}
unit_ids = set(ids)
if combats_arr and combats_arr.get("data"):
    for i in range(combats_arr["size"]):
        cp = u64(combats_arr["data"] + i * 8)
        rec = {"slot": i, "ptr": hex(cp) if cp else None, "rtti": class_of(cp)}
        if looks_ptr(cp):
            blob = p.try_read(cp, 0x400) or b""
            # scan for our unit ids as u32, and army pointers
            hits_id, hits_ptr, ptr_rtti = [], [], []
            for off in range(0, len(blob) - 3, 4):
                val = struct.unpack_from("<I", blob, off)[0]
                if val in unit_ids:
                    hits_id.append({"off": off, "id": val})
            for off in range(0, len(blob) - 7, 8):
                val = struct.unpack_from("<Q", blob, off)[0]
                for u in units:
                    if val == u["ptr"]:
                        hits_ptr.append({"off": off, "id": u["id"]})
                if looks_ptr(val):
                    nm = class_of(val)
                    if nm:
                        ptr_rtti.append({"off": off, "rtti": nm, "ptr": hex(val)})
            rec["unit_id_hits"] = hits_id[:40]
            rec["army_ptr_hits"] = hits_ptr
            rec["ptr_rtti"] = ptr_rtti[:40]
            # also scan arrays of handles (type 0x33 + index)
            handle_hits = []
            for off in range(0, len(blob) - 7, 4):
                typ = struct.unpack_from("<I", blob, off)[0]
                ix = struct.unpack_from("<I", blob, off+4)[0]
                if typ == 0x33 and ix in unit_ids:
                    handle_hits.append({"off": off, "id": ix})
            rec["handle_hits"] = handle_hits
        combat_info["items"].append(rec)

# in_combat candidates: bool/i32/ptr that split units mentioned in combats vs not
combat_unit_ids = set()
for rec in combat_info["items"]:
    for h in rec.get("handle_hits", []) + rec.get("unit_id_hits", []) + rec.get("army_ptr_hits", []):
        combat_unit_ids.add(h["id"])
in_combat_fields = []
if combat_unit_ids:
    label = [1 if u["id"] in combat_unit_ids else 0 for u in units]
    for off, ivals in int_rows.items():
        # 0/1 bool
        vals = [0 if v in (0, None) else 1 for v in ivals]
        if vals == label:
            in_combat_fields.append({"off": off, "kind": "i32_bool_match", "values": ivals})
    for off, info in ptr_rows.items():
        vals = [1 if looks_ptr(pv) else 0 for pv in info["ptrs"]]
        if vals == label:
            in_combat_fields.append({"off": off, "kind": "ptr_bool_match", "rtti": sorted({r for r in info["rtti"] if r}), "values": [hex(pv) if looks_ptr(pv) else pv for pv in info["ptrs"]]})

# follow officer pointers for names
officer_names = []
for field in officer_fields:
    if field["kind"] != "ptr_exact":
        continue
    off = field["off"]
    for u, pv_hex in zip(units, field["values"]):
        if not u["exp"].get("officer"):
            continue
        try:
            pv = int(pv_hex, 16) if isinstance(pv_hex, str) else pv_hex
        except Exception:
            continue
        strings = []
        # search first 0x200 for pdx strings / utf8
        for s_off in range(0, 0x200, 8):
            s = read_pdx_string(pv + s_off)
            if s and len(s) >= 3:
                strings.append({"off": s_off, "s": s})
            elif looks_ptr(u64(pv + s_off)):
                s2 = read_pdx_string(u64(pv + s_off)) if False else read_utf8(u64(pv + s_off))
                # also try +0x60 style
                child = u64(pv + s_off)
                if looks_ptr(child):
                    for c_off in (0, 0x10, 0x18, 0x20, 0x40, 0x60, 0x80):
                        s3 = read_pdx_string(child + c_off)
                        if s3 and len(s3) >= 3:
                            strings.append({"via": hex(s_off)+"+"+hex(c_off), "s": s3, "child_rtti": class_of(child)})
        officer_names.append({"unit_id": u["id"], "expected": u["exp"].get("officer"), "field_off": off, "rtti": class_of(pv), "strings": strings[:20]})

# theatre / army group pointers from country
theatres = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_THEATRES"])
th_rtti = []
if theatres and theatres.get("data"):
    for i in range(theatres["size"]):
        th = u64(theatres["data"] + i * 8)
        th_rtti.append({"i": i, "ptr": hex(th) if th else None, "rtti": class_of(th)})

# report compact
def pack_hits(hits, kind):
    out = []
    for item in hits[:12]:
        if kind in ("eq", "xp", "org"):
            off, n, tot, err, vals = item[0], item[1], item[2], item[3], item[4]
            out.append({"off": off, "match": n, "tot": tot, "mae": round(err, 6), "values": vals})
        else:
            off, n, tot, vals = item
            out.append({"off": off, "match": n, "tot": tot, "values": vals})
    return out

# interesting floats even if not exact: 0-1 varying with eq, or 0-100 with org
soft_eq = []
for off, fvals in float_rows.items():
    if any(v is None for v in fvals):
        continue
    if any(v < -0.05 or v > 1.15 for v in fvals):
        continue
    err = mae(fvals, eqs)
    if err <= 0.08:
        soft_eq.append({"off": off, "mae": round(err, 6), "values": [round(v, 5) for v in fvals]})
soft_eq.sort(key=lambda x: x["mae"])

soft_xp = []
for off, fvals in float_rows.items():
    if any(v is None for v in fvals):
        continue
    if any(v < -0.05 or v > 1.15 for v in fvals):
        continue
    err = mae(fvals, xps)
    if err <= 0.08:
        soft_xp.append({"off": off, "mae": round(err, 6), "values": [round(v, 5) for v in fvals]})
soft_xp.sort(key=lambda x: x["mae"])

soft_org = []
for off, fvals in float_rows.items():
    if any(v is None for v in fvals):
        continue
    if any(v < 0 or v > 120 for v in fvals):
        continue
    # cluster by template
    err = mae(fvals, orgs)
    if err <= 5:
        soft_org.append({"off": off, "mae": round(err, 4), "values": [round(v, 4) for v in fvals]})
soft_org.sort(key=lambda x: x["mae"])

# 0-1 supply-like: maybe all ~1 if in supply at start
soft_01 = []
for off, fvals in float_rows.items():
    if any(v is None for v in fvals):
        continue
    if any(v < -0.02 or v > 1.2 for v in fvals):
        continue
    uniq = len({round(v, 4) for v in fvals})
    mean = sum(fvals)/len(fvals)
    if uniq >= 2 or (0.5 <= mean <= 1.05):
        # skip if already listed as eq/xp exact-ish
        soft_01.append({"off": off, "uniq": uniq, "mean": round(mean, 5), "values": [round(v, 5) for v in fvals]})

fields = summary.get("fields") or {}
date_full = fields.get("date_full") or {}

brief = {
    "pid": p.pid,
    "player": {"index": player_index, "tag": player_tag},
    "game_time": date_full,
    "speed_notch": fields.get("game_speed_notch"),
    "hour_progress": fields.get("game_hour_progress"),
    "unit_count": len(units),
    "eq_exact": pack_hits(sorted(eq_hits, key=lambda x: (-x[1], x[3])), "eq"),
    "eq_soft": soft_eq[:10],
    "xp_exact": pack_hits(sorted(xp_hits, key=lambda x: (-x[1], x[3])), "xp"),
    "xp_soft": soft_xp[:10],
    "org_exact": pack_hits(sorted(org_hits, key=lambda x: (-x[1], x[3])), "org"),
    "org_soft": soft_org[:10],
    "mp_exact": pack_hits(sorted(mp_hits, key=lambda x: -x[1]), "mp"),
    "width_exact": pack_hits(sorted(width_hits, key=lambda x: -x[1]), "w"),
    "officer_fields": officer_fields[:20],
    "officer_names": officer_names,
    "combat": combat_info,
    "combat_unit_ids": sorted(combat_unit_ids),
    "in_combat_fields": in_combat_fields[:20],
    "path_like": [
        {"off": x["off"], "nonempty": x["nonempty"], "rtti": x["rtti"],
         "sizes": [None if m is None else m.get("size") for m in x["meta"]],
         "heads": x["samples"]}
        for x in path_like if x["nonempty"] or x["off"] in (CA_PATH, 0x200)
    ],
    "rtti_in_carmy": {k: v for k, v in sorted(rtti_map.items(), key=lambda kv: -len(kv[1]))},
    "theatres": th_rtti,
}

# add a few always-interesting offsets even if not hits
interesting_offs = [0xB8, 0x138, 0x1E0, 0x1F0, 0x200, 0x340, 0x3B8]
snap = []
for u in units:
    rec = {"id": u["id"], "name": u["exp"].get("name"), "ptr": hex(u["ptr"]),
           "expected_eq": u["exp"].get("eq"), "expected_xp": u["exp"].get("xp"),
           "expected_mp": u["exp"].get("mp"), "officer": u["exp"].get("officer")}
    for off in interesting_offs:
        rec["off_%x" % off] = {
            "u32": int_rows[off][units.index(u)] if off in int_rows else None,
            "f32": None if off not in float_rows or float_rows[off][units.index(u)] is None else round(float_rows[off][units.index(u)], 5),
        }
        if off % 8 == 0 and off in ptr_rows:
            pv = ptr_rows[off]["ptrs"][units.index(u)]
            rec["off_%x" % off]["ptr"] = hex(pv) if looks_ptr(pv) else pv
            rec["off_%x" % off]["rtti"] = ptr_rows[off]["rtti"][units.index(u)]
            rec["off_%x" % off]["array"] = ptr_rows[off]["arrays"][units.index(u)]
    snap.append(rec)
brief["unit_snap"] = snap

OUT.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
# compact stdout: don't dump huge rtti/path if empty
show = {k: brief[k] for k in brief if k not in ("unit_snap",)}
# shrink rtti
show["rtti_in_carmy"] = {k: offs[:12] + (["..."] if len(offs) > 12 else []) for k, offs in brief["rtti_in_carmy"].items()}
print(json.dumps(show, ensure_ascii=False, indent=2))
p.close()
