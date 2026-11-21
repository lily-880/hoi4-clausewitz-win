from __future__ import annotations
import json, struct, sys, bisect
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

sys.path.insert(0, "calling")
from pe import PE

EXE = r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe"
pe = PE(EXE)
cs = Cs(CS_ARCH_X86, CS_MODE_64)
pd = next(s for s in pe.sections if s.name == ".pdata")
raw = pe.data[pd.raw_ptr:pd.raw_ptr + pd.raw_size]
functions = []
for i in range(0, len(raw) - 11, 12):
    start, end, _unwind = struct.unpack_from("<III", raw, i)
    if start and end and end > start:
        functions.append((start, end))
starts = [s for s, e in functions]


def func_of(target):
    i = bisect.bisect_right(starts, target) - 1
    if i < 0:
        return None
    start, end = functions[i]
    if start <= target < end:
        return start, end
    return None


def rva_to_off(rva):
    return pe.rva_to_off(rva)


def read_rva(rva, n):
    off = rva_to_off(rva)
    if off is None:
        return b""
    return pe.data[off:off + n]


def disasm_fn(start, end, limit=0x400):
    blob = read_rva(start, min(end - start, limit))
    out = []
    for i in cs.disasm(blob, start):
        out.append({"rva": hex(i.address), "asm": i.mnemonic + " " + i.op_str})
    return out


def calls_to(code, target_rva):
    hits = []
    for ins in code:
        asm = ins["asm"]
        if asm.startswith("call ") or asm.startswith("jmp "):
            # immediates like 0x23f5d40
            if hex(target_rva) in asm.replace("0x0", "0x"):
                hits.append(ins)
            # also un-padded
            if f"{target_rva:x}" in asm.lower():
                hits.append(ins)
    # unique
    uniq = []
    seen = set()
    for h in hits:
        if h["rva"] not in seen:
            seen.add(h["rva"])
            uniq.append(h)
    return uniq


targets = {
    "old_POST": 0x22C41E0,
    "new_POST_plus70": 0x22C4250,
    "old_SESSION_UPDATE": 0x22C6410,
    "new_SESSION_UPDATE_plus70": 0x22C6480,
    "old_SINK": 0x23F5CD0,
    "new_SINK": 0x23F5D40,
    "old_DRAIN": 0x23F64E0,
    "new_DRAIN": 0x23F6550,
}

info = {}
for name, rva in targets.items():
    bounds = func_of(rva)
    rec = {"target": hex(rva), "function": hex(bounds[0]) if bounds else None, "end": hex(bounds[1]) if bounds else None}
    if bounds:
        start, end = bounds
        rec["size"] = end - start
        code = disasm_fn(start, end, min(end - start, 0x800))
        rec["n_ins"] = len(code)
        rec["head"] = code[:16]
        rec["calls_new_sink"] = calls_to(code, 0x23F5D40)
        rec["calls_old_sink"] = calls_to(code, 0x23F5CD0)
        rec["calls_new_drain"] = calls_to(code, 0x23F6550)
        rec["calls_G_SESSION_lea"] = [c for c in code if "0x34ffbe8" in c["asm"].lower() or "34ffbe8" in c["asm"].lower()]
        rec["calls_old_plus_slide"] = [c for c in code if any(s in c["asm"].lower() for s in ("22c4250", "22c6480"))]
    info[name] = rec

# Also search which functions call new sink (within .text, via pdata function starts that call it)
# cheaper: scan .text for E8 rel to 0x23F5D40
text = next(s for s in pe.sections if s.name == ".text")
chunk = pe.data[text.raw_ptr:text.raw_ptr + text.raw_size]
sink_callers = []
# E8 rel32: rel = target - (ip+5); ip = text.va + offset
target = 0x23F5D40
for off in range(0, len(chunk) - 4):
    if chunk[off] != 0xE8:
        continue
    rel = struct.unpack_from("<i", chunk, off + 1)[0]
    ip = text.virtual_address + off
    if ip + 5 + rel == target:
        sink_callers.append(hex(ip))
        if len(sink_callers) >= 30:
            break

out = {"functions": info, "e8_callers_of_new_sink": sink_callers, "n_callers_capped": len(sink_callers)}
Path("research/t191_post_disasm.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
# compact
print(json.dumps({
    k: {
        "function": v.get("function"),
        "end": v.get("end"),
        "size": v.get("size"),
        "head": v.get("head"),
        "calls_new_sink": v.get("calls_new_sink"),
        "calls_old_sink": v.get("calls_old_sink"),
        "calls_new_drain": v.get("calls_new_drain"),
        "g_session": v.get("calls_G_SESSION_lea"),
    } for k, v in info.items()
}, indent=2))
print("new_sink_e8_callers", sink_callers)
