import os, sys, json, struct
from pathlib import Path
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import _pdx_array, resolve_player_country
from handle import resolve_handle, HANDLE_TYPE_ARMY, HANDLE_TYPE_TABLE
from country_tags import tag_for_index

CA_HANDLE = 0x18
CA_PROVINCE_ID = 0x28
CA_COUNTRY_TAG = 0x1E0
CA_DIV_TEMPLATE = 0x3B8
CA_NAME_MEMBER = 0x340
TMPL_NAME = 0x20
CNG_DISPLAY_NAME = 0x60
CA_PROVINCE = 0x1F0
CP_ID = 0xA4

p = Proc(find_pid(config.EXE_NAME))

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
def looks_ptr(x):
    return bool(x) and 0x10000 < x < 0x7FFFFFFFFFFF
def read_utf8(addr, n=128):
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
    ptr = u64(addr)
    if looks_ptr(ptr):
        s = read_utf8(ptr)
        if s:
            return s
    return read_utf8(addr)
def tmpl_name(ap):
    tmpl = u64(ap + CA_DIV_TEMPLATE)
    return read_pdx_string(tmpl + TMPL_NAME) if looks_ptr(tmpl) else None
def unit_name(ap):
    member = u64(ap + CA_NAME_MEMBER)
    return read_pdx_string(member + CNG_DISPLAY_NAME) if looks_ptr(member) else None

gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
resolved = resolve_player_country(p, gs)
idx = resolved["player_index"]
countries = _pdx_array(p, gs + O.HYPOTHESIS_STRUCT["GS_COUNTRIES"])
cptr = u64(countries["data"] + idx * 8)
armies = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_ARMIES"])
theatres = _pdx_array(p, cptr + O.HYPOTHESIS_STRUCT["CO_THEATRES"])

print("player", idx, resolved.get("tag"), "cptr", hex(cptr) if cptr else None)
print("CO_ARMIES", armies)

th_info = []
th_army_ptrs = []
if theatres and theatres.get("data"):
    for i in range(theatres["size"]):
        th = u64(theatres["data"] + i * 8)
        arr = _pdx_array(p, th + O.HYPOTHESIS_STRUCT["TH_ARMIES"]) if th else None
        rec = {"i": i, "th": hex(th) if th else None, "armies": arr}
        th_info.append(rec)
        if arr and arr.get("data"):
            for j in range(arr["size"]):
                th_army_ptrs.append(u64(arr["data"] + j * 8))
print("theatres", len(th_info), "th_army_ptrs", len(th_army_ptrs))
for rec in th_info:
    a = rec["armies"]
    print("  th", rec["i"], rec["th"], "size", None if not a else a["size"], "cap", None if not a else a["capacity"])

# walk handle table: try indices 1..20000
usa = []
seen = set()
for ix in range(1, 20001):
    try:
        obj = resolve_handle(b, HANDLE_TYPE_ARMY, ix, p.base)
    except Exception:
        continue
    if not obj or obj in seen:
        continue
    seen.add(obj)
    tag = i32(obj + CA_COUNTRY_TAG)
    if tag != idx:
        continue
    h_ty, h_ix = u32(obj + CA_HANDLE), u32(obj + CA_HANDLE + 4)
    usa.append({
        "unit_id": h_ix,
        "ptr": hex(obj),
        "province_id": u32(obj + CA_PROVINCE_ID),
        "owner_index": tag,
        "name": unit_name(obj),
        "template": tmpl_name(obj),
        "in_co_armies": obj in ([u64(armies["data"] + k*8) for k in range(armies["size"])] if armies and armies.get("data") else []),
        "in_th_armies": obj in th_army_ptrs,
        "handle_ok": h_ty == HANDLE_TYPE_ARMY and h_ix == ix,
    })

print("HANDLE_USA", len(usa), "scanned_hits_any", len(seen))
print(json.dumps(usa, ensure_ascii=False, indent=2))
p.close()
