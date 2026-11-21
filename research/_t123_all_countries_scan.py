import json, os, struct, sys, collections
sys.path.insert(0, os.path.join(os.getcwd(), "calling"))
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"

import config, offsets as O
from gamestate import _pdx_array
from mem import Proc, find_pid
from clock import ui_date, ui_hour

p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
player = struct.unpack_from("<i", p.try_read(gs + O.HYPOTHESIS_STRUCT["GS_PLAYER_TAG"], 4), 0)[0]

CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_DIV_TEMPLATE = 0x3B8
TMPL_NAME = 0x20
CO_ARMIES = O.HYPOTHESIS_STRUCT["CO_ARMIES"]
CO_TEMPLATES = O.HYPOTHESIS_STRUCT["CO_DIV_TEMPLATES"]
CO_STATES = O.HYPOTHESIS_STRUCT["CO_STATES"]
CO_FLEETS = O.HYPOTHESIS_STRUCT["CO_FLEETS"]

ETH_PROVS = {5010, 1984, 13237, 13238, 2072, 5097, 7980, 7944, 12812, 12757, 4995, 8062}
SPR_PROVS = {3938, 7183, 6906, 9764, 3816, 885, 11825, 758, 13071, 740, 11707, 1048, 9793, 9945, 12100}
ETH_NAME_NEEDLES = ("Sefari", "Kebur", "Chitet", "Mehal", "Zabagna", "Ethiop", "Goijam", "Gojjam")
SPR_NAME_NEEDLES = ("División", "Division de", "Brigada", "Infantería", "Caballería", "Montaña")

def u32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<I", b, 0)[0] if b else None

def i32(addr):
    b = p.try_read(addr, 4)
    return struct.unpack_from("<i", b, 0)[0] if b else None

def u64(addr):
    b = p.try_read(addr, 8)
    return struct.unpack_from("<Q", b, 0)[0] if b else None

def read_utf8(addr, n=96):
    b = p.try_read(addr, n)
    if not b:
        return None
    s = b.split(b"\0", 1)[0]
    try:
        t = s.decode("utf-8")
    except Exception:
        return None
    return t if t else None

def read_tmpl_name(army_ptr):
    tmpl = u64(army_ptr + CA_DIV_TEMPLATE) if army_ptr else None
    if not tmpl:
        return None
    # name pointer at +0x20, or inline?
    ptr = u64(tmpl + TMPL_NAME)
    if ptr and 0x10000 < ptr < 0x7FFFFFFFFFFF:
        return read_utf8(ptr)
    # maybe SSO / inline
    return read_utf8(tmpl + TMPL_NAME)

def ascii_tag_hits(blob):
    hits = []
    if not blob:
        return hits
    for needle in (b"ETH", b"SPR", b"SPA", b"SPN", b"HAI", b"ITA", b"ENG", b"GER", b"SOV", b"USA", b"FRA", b"JAP", b"CHI"):
        idx = 0
        while True:
            i = blob.find(needle, idx)
            if i < 0:
                break
            # require non-alpha neighbors when possible
            pre = blob[i-1:i] if i > 0 else b""
            post = blob[i+3:i+4]
            ok_pre = (not pre) or not (pre.isalpha())
            ok_post = (not post) or not (post.isalpha())
            if ok_pre and ok_post:
                hits.append({"off": i, "tag": needle.decode()})
            idx = i + 1
    return hits

year = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_YEAR"])
day_index = i32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOURS"])
hour_tick = u32(gs + O.HYPOTHESIS_STRUCT["GS_DATE_HOUR_TICK"])
shown = ui_date(year, day_index) if year else None

# nearby ints around GS_PLAYER_TAG that could be alternate player indices
nearby = {}
for off in range(0x500, 0x540, 4):
    nearby[hex(off)] = i32(gs + off)

# TAG2INDEX array header
tag2 = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_TAG2INDEX"])

n_countries = countries["size"] if countries else 0
rows = []
eth_hits = []
spr_hits = []
size21 = []

for idx in range(n_countries):
    cptr = u64(countries["data"] + idx * 8)
    if not cptr:
        continue
    armies = _pdx_array(p, cptr + CO_ARMIES)
    templates = _pdx_array(p, cptr + CO_TEMPLATES)
    states = _pdx_array(p, cptr + CO_STATES)
    fleets = _pdx_array(p, cptr + CO_FLEETS)
    army_n = armies["size"] if armies and armies.get("size") is not None else None
    if not army_n or army_n <= 0 or army_n > 2000:
        # still record if templates/states look live
        if not (states and 0 < states.get("size", 0) <= 200):
            continue
    provs = []
    names = []
    if armies and 0 < army_n <= 400:
        take = min(army_n, 40)
        for i in range(take):
            ap = u64(armies["data"] + i * 8)
            if not ap:
                continue
            pid = u32(ap + CA_PROVINCE_ID)
            nm = read_tmpl_name(ap)
            if pid:
                provs.append(pid)
            if nm:
                names.append(nm)
    prov_set = set(provs)
    eth_n = len(prov_set & ETH_PROVS)
    spr_n = len(prov_set & SPR_PROVS)
    name_eth = [n for n in names if any(s.lower() in n.lower() for s in ETH_NAME_NEEDLES)]
    name_spr = [n for n in names if any(s in n for s in SPR_NAME_NEEDLES)]
    # scan first 0x200 of country for 3-letter tags
    blob = p.try_read(cptr, 0x200) or b""
    tags = ascii_tag_hits(blob)
    rec = {
        "index": idx,
        "cptr": hex(cptr),
        "armies": army_n,
        "templates": templates["size"] if templates else None,
        "states": states["size"] if states else None,
        "fleets": fleets["size"] if fleets else None,
        "prov_sample": provs[:12],
        "name_sample": names[:8],
        "eth_prov_hits": eth_n,
        "spr_prov_hits": spr_n,
        "eth_name_hits": name_eth[:6],
        "spr_name_hits": name_spr[:6],
        "tag_hits_0x200": tags[:8],
        "is_claimed_player": idx == player,
    }
    interesting = (
        idx == player
        or eth_n
        or spr_n
        or name_eth
        or (army_n in (13, 17, 21) if army_n else False)
        or tags
    )
    if interesting:
        rows.append(rec)
    if eth_n or name_eth:
        eth_hits.append(rec)
    if spr_n or name_spr:
        spr_hits.append(rec)
    if army_n == 21:
        size21.append(rec)

# Also try TAG2INDEX if it looks like a map from packed tags
tag2_info = {"raw": tag2}
# Heuristic: some HOI4 builds store tag as packed 3 chars in u32
def pack_tag(s):
    b = s.encode("ascii")
    v = 0
    for i, ch in enumerate(b):
        v |= ch << (8 * i)
    return v

def lookup_packed(tag):
    # try common layouts later; just record packed values
    return pack_tag(tag)

# Scan country object of claimed player and of any ETH hit for printable strings
def strings_near(ptr, n=0x800):
    b = p.try_read(ptr, n) or b""
    out = []
    i = 0
    while i < len(b):
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and 32 <= b[j] < 127:
                j += 1
            if j - i >= 3:
                s = b[i:j].decode("ascii", "ignore")
                if any(c.isalpha() for c in s):
                    out.append({"off": i, "s": s[:80]})
            i = j + 1
        else:
            i += 1
    return out

player_cptr = u64(countries["data"] + player * 8) if 0 <= player < n_countries else 0
extra_string_scans = {}
if player_cptr:
    extra_string_scans["player"] = strings_near(player_cptr, 0x600)
for rec in eth_hits[:3]:
    extra_string_scans["eth_%s" % rec["index"]] = strings_near(int(rec["cptr"], 16), 0x600)

out = {
    "pid": p.pid if hasattr(p, "pid") else None,
    "gs": hex(gs),
    "date": {"year": year, "ui": shown, "day_index": day_index, "ui_hour": ui_hour(hour_tick) if hour_tick is not None else None},
    "countries_size": n_countries,
    "claimed_player_index": player,
    "nearby_0x500_0x53c": nearby,
    "tag2index": tag2_info,
    "interesting_countries": rows,
    "eth_hits": [{"index": r["index"], "armies": r["armies"], "eth_prov_hits": r["eth_prov_hits"], "eth_name_hits": r["eth_name_hits"], "states": r["states"]} for r in eth_hits],
    "spr_hits": [{"index": r["index"], "armies": r["armies"], "spr_prov_hits": r["spr_prov_hits"], "spr_name_hits": r["spr_name_hits"], "states": r["states"]} for r in spr_hits],
    "size21": [{"index": r["index"], "armies": r["armies"], "states": r["states"], "name_sample": r["name_sample"], "prov_sample": r["prov_sample"]} for r in size21],
    "string_scans_preview": {k: v[:20] for k, v in extra_string_scans.items()},
}

path = os.path.join("research", "_t123_all_countries_scan.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(json.dumps({
    "date": out["date"],
    "countries_size": n_countries,
    "claimed_player_index": player,
    "eth_hits": out["eth_hits"],
    "spr_hits": out["spr_hits"],
    "size21": out["size21"],
    "interesting_n": len(rows),
}, ensure_ascii=False, indent=2))
print("WROTE", path)
