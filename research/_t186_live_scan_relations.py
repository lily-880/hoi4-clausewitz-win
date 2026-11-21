import sys,os,re,json,struct,collections
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, resolve_player_country, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
IMAGE=pe.image_base
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

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
        if i.mnemonic=="ret" and i.address>start+12:
            break
    if path:
        Path(path).write_text("\n".join(lines)+"\n", encoding="utf-8")
    return lines

print("======= FULL 0xd8f520 =====")
print("\n".join(clip(0xd8f520, 0x120)))

print("\n======= CRelationStatus writer 0xd8f5c0 =====")
lines=clip(0xd8f5c0, 0x300, "research/_t186_clip_relationstatus_writer_0xd8f5c0.txt")
for ln in lines:
    if "TOKEN" in ln or "call" in ln or "[" in ln and "ptr" in ln:
        print(ln)

print("\n======= CDiplomacyStatus writer 0xdad1a0 (tokens) =====")
lines=clip(0xdad1a0, 0x800, "research/_t186_clip_diplomacystatus_writer_0xdad1a0.txt")
print("n", len(lines), "last", lines[-1] if lines else None)
for ln in lines:
    if "TOKEN" in ln:
        print(ln)

# switch tables for hostility
# after 0xd8fb07 mov ecx, [rsi+rax*4+0xd8fbb8]
# rsi at that point? need to see lea rsi
raw=pe.read_rva(0xd8fbb8, 0x40) or b""
print("\n======= switch tables =====")
# This is typically a jump table of rel32 from a base. Or absolute? 
# mov ecx, dword [rsi + rax*4 + 0xd8fbb8]; add rcx, rsi; jmp rcx
# so entries are rel32 from rsi. What is rsi? Look at instruction before cmp eax,5

p=Proc(find_pid("hoi4.exe"))
try:
    def cls(a):
        if not a or a<0x10000 or a>0x7fffffffffff: return None
        try:
            vt=p.ptr(a)
        except Exception:
            return None
        if not vt or not (p.base<=vt<p.base+p.image_size): return None
        try:
            return _rtti_name_from_vtable(pe, vt-p.base)
        except Exception:
            return None

    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)

    want_names=("WarRelation","RelationStatus","DiplomacyStatus","Relation@@","Truce")
    # scan GS first 0x900 for vtables or pointers
    def scan(base, size, label):
        blob=p.try_read(base, size) or b""
        hits=[]
        for off in range(0, len(blob)-7, 8):
            v=struct.unpack_from("<Q", blob, off)[0]
            name=None
            kind="vt"
            obj=None
            if p.base<=v<p.base+p.image_size:
                name=_rtti_name_from_vtable(pe, v-p.base)
            elif 0x10000<v<0x7fffffffffff:
                name=cls(v)
                kind="ptr"
                obj=v
            if name and any(k in name for k in ("War","Relation","Diplomacy","Truce","PeaceConference")):
                # skip noise UI if any
                hits.append({"off":hex(off),"kind":kind,"val":hex(v),"name":name})
        print(f"\n===== {label} hits {len(hits)} =====")
        for h in hits:
            print(h)
        return hits

    scan(gs, 0x900, "GS 0x900")
    scan(co, 0x800, "CCountry 0x800")
    # also common later country offsets — CCountry can be large
    scan(co, 0x2000, "CCountry 0x2000")
finally:
    p.close()
