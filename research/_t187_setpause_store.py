import sys,re,json,os,struct
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from gamestate import detect_session, read_campaign_summary
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}

raw=pe.read_rva(0xe487f0, 0x800) or b""
lines=[]
for i in cs.disasm(raw, 0xe487f0):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
    if m:
        tok=int(m.group(2),16)
        if tok in id2name:
            a += "  ; TOKEN "+id2name[tok]
    lines.append(a)
    if i.mnemonic=="ret" and i.address>0xe48820:
        break
Path("research/_t187_clip_idler_setpause_0xe487f0.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("n", len(lines), "last", lines[-1])
print("--- 0x6c0 / 0x6c1 / r14 / stores ---")
for ln in lines:
    if any(k in ln for k in ("0x6c0","0x6c1","r14","mov byte","TOKEN pause","TOKEN speed")):
        print(ln)

p=Proc(find_pid("hoi4.exe"))
try:
    session=detect_session(p, pe)
    idler=int(session["signals"]["idler_ptr"],16)
    gs=int(session["signals"]["gs_ptr"],16)
    summary=read_campaign_summary(p, gs)
    ver=summary.get("verified",{})
    raw=p.try_read(idler+0x6b8, 0x20) or b""
    rec={
        "idler": hex(idler),
        "b6c0": p.read(idler+0x6c0,1)[0],
        "b6c1": p.read(idler+0x6c1,1)[0],
        "b6c2": p.read(idler+0x6c2,1)[0],
        "b6c3": p.read(idler+0x6c3,1)[0],
        "bytes_6b8_6d0": raw.hex(),
        "gs_4b8_f32": struct.unpack("<f", p.read(gs+0x4b8,4))[0],
        "gs_4bc_i32": p.i32(gs+0x4bc),
        "speed_notch": ver.get("game_speed_notch"),
        "hour_progress": ver.get("game_hour_progress"),
        "hour_tick": (ver.get("date_full") or {}).get("hour_tick"),
    }
    print(json.dumps(rec, indent=2))
    Path("research/t187_live_pause.json").write_text(json.dumps(rec, indent=2)+"\n", encoding="utf-8")
finally:
    p.close()
