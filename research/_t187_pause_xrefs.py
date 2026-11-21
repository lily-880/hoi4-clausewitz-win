import sys,re,json,struct,bisect
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import _rtti_name_from_vtable

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base
cs=Cs(CS_ARCH_X86, CS_MODE_64)
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

def token_xrefs(tok):
    imm=struct.pack("<I", tok)
    funcs=set(); hits=[]
    for prefix in (b"\xba", b"\xb8", b"\xb9", b"\x41\xba", b"\x41\xb8", b"\x41\xb9"):
        for m in re.finditer(re.escape(prefix+imm), text_raw):
            at=text_rva+m.start()
            fo=func_of(at)
            f=fo[0] if fo else None
            funcs.add(f)
            hits.append((hex(at), hex(f) if f else None, prefix.hex()))
    return sorted(x for x in funcs if x), hits

name2tok={i["name"]:i["token"] for i in mp}
print("===== token xref funcs =====")
for n in ("paused","pausegame","pause_game","unpause_game","pause_with_no_player","unit_controller_pause","pause_on_popups","pause_on_loop","speed"):
    tok=name2tok[n]
    funcs,hits=token_xrefs(tok)
    print(n, hex(tok), "hits", len(hits), "funcs", [hex(f) for f in funcs[:20]], "nfunc", len(funcs))

# strings
needles=[b"IsPaused", b"SetPaused", b"is_paused", b"IsGamePaused", b"_Paused", b"bPaused", b"GamePaused", b"pausegame", b"PauseGame", b"UnpauseGame", b"Game is paused", b"game_paused"]
print("\n===== strings =====")
for s in pe.sections:
    blob=pe.data[s.raw_ptr:s.raw_ptr+s.raw_size]
    for n in needles:
        for m in re.finditer(re.escape(n), blob):
            rva=s.virtual_address+m.start()
            start=max(0,m.start()-30)
            ctx=bytes(b if 32<=b<127 else 0x2e for b in blob[start:m.start()+len(n)+40])
            print(f"  {s.name} {hex(rva)} {n.decode()} ctx={ctx}")
