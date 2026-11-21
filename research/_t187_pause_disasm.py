import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
IMAGE=pe.image_base
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
pd=next(s for s in pe.sections if s.name==".pdata")
raw_pd=pe.data[pd.raw_ptr:pd.raw_ptr+pd.raw_size]
functions=[struct.unpack_from("<III", raw_pd, o)[:2] for o in range(0,len(raw_pd)-11,12)]
starts=[x[0] for x in functions]
text=next(s for s in pe.sections if s.name==".text")
text_raw=pe.data[text.raw_ptr:text.raw_ptr+text.raw_size]
text_rva=text.virtual_address

def func_of(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i<0: return None
    s,e=functions[i]
    return (s,e) if s<=rva<e else None

def clip(start, nbytes, path=None):
    raw=pe.read_rva(start, nbytes) or b""
    lines=[]
    for i in cs.disasm(raw, start):
        a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
        m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
        if m:
            tok=int(m.group(2),16)
            if tok in id2name:
                a += "  ; TOKEN "+id2name[tok]
        lines.append(a)
        if i.mnemonic=="ret" and i.address>start+8:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

fo=func_of(0x2f54d3)
print("paused token func", fo, "size", hex(fo[1]-fo[0]) if fo else None)
start=fo[0] if fo else 0x2f5400
lines=clip(start, min((fo[1]-fo[0]+0x40) if fo else 0x200, 0x400), "research/_t187_clip_paused_token_0x2f54d3.txt")
print("======= paused token container =====")
# show around 0x2f54d3 and all tokens
for ln in lines:
    if "TOKEN" in ln or "0x2f54d" in ln or "call 0x597c00" in ln or "jmp 0x597c00" in ln:
        print(ln)
print("first 20:")
print("\n".join(lines[:20]))
print("n", len(lines), "last", lines[-1] if lines else None)

# pausegame string xrefs 0x2b47d48
def lea_xrefs(rva, limit=20):
    hits=[]
    for m in re.finditer(b"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x2d\x35\x3d]", text_raw):
        at=m.start()
        rel=struct.unpack_from("<i", text_raw, at+3)[0]
        dest=text_rva+at+7+rel
        if dest==rva:
            fo=func_of(text_rva+at)
            hits.append((hex(text_rva+at), hex(fo[0]) if fo else None))
            if len(hits)>=limit: break
    return hits

# find exact start of pausegame string
print("\npausegame lea", lea_xrefs(0x2b47d48))
# also nearby starts
raw=pe.read_rva(0x2b47d40, 0x20) or b""
print("around pausegame", raw)

# CPauseGame vtable / writer
from gamestate import _rtti_name_from_vtable
# unit_controller_pause in ced2e0 - just confirm offset
print("\n===== unit_controller_pause in CArmy writer =====")
# search in known clip if exists
for p in Path("research").glob("*ced2e0*"):
    t=p.read_text(encoding="utf-8", errors="replace")
    if "35ba" in t or "unit_controller_pause" in t:
        for ln in t.splitlines():
            if "35ba" in ln or "pause" in ln.lower():
                print(p.name, ln)

# more strings: PAUSED, Pause, "paused" utf8/utf16
print("\n===== more pause strings =====")
for s in pe.sections:
    if s.name not in (".rdata",".data",".text"): 
        # also check all rdata-like
        pass
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for n in (b"PAUSED", b"Game Paused", b"is paused", b"_isPaused", b"IsPaused(", b"GetPaused", b"SetGamePaused", b"bIsPaused", b"m_bPaused", b"Paused =", b"paused ="):
        for m in re.finditer(re.escape(n), blob):
            rva=s.virtual_address+m.start()
            ctx=bytes(b if 32<=b<127 else 0x2e for b in blob[max(0,m.start()-20):m.start()+len(n)+40])
            print(s.name, hex(rva), n, ctx)
    # utf16 PAUSED
    for n in (b"P\x00A\x00U\x00S\x00E\x00D\x00", b"P\x00a\x00u\x00s\x00e\x00d\x00"):
        if n in blob:
            print(s.name, "utf16", n, "at", hex(s.virtual_address+blob.find(n)))
