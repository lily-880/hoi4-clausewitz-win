import sys,re,json,struct,os
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, _pdx_array
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
raw=pe.read_rva(0xcc6570, 0x80) or b""
print("======= CC6570 =====")
for i in cs.disasm(raw, 0xcc6570):
    print(f"0x{i.address:x}  {i.mnemonic} {i.op_str}")
    if i.mnemonic=="ret":
        break

# dump one live CArmyManpower
p=Proc(find_pid("hoi4.exe"))
def u64(a):
    b=p.try_read(a,8)
    return struct.unpack("<Q", b)[0] if b and len(b)==8 else None
def i32(a):
    b=p.try_read(a,4)
    return struct.unpack("<i", b)[0] if b and len(b)==4 else None
try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    eth=int(res["country_ptr"],16)
    th=_pdx_array(p, eth+0x168)
    tp=u64(int(th["data"]))
    ua=_pdx_array(p, tp+0x68)
    ca=u64(int(ua["data"]))
    mp=ca+0x3d0
    blob=p.try_read(mp, 0x80) or b""
    print("ca", hex(ca), "mp", hex(mp), "uid", i32(ca+0x1c))
    print("hex", blob.hex())
    for off in range(0, 0x80, 8):
        q=struct.unpack_from("<Q", blob, off)[0]
        d=struct.unpack_from("<ii", blob, off)
        print(f"  +{off:02x} q={q:016x} i32={d}")
finally:
    p.close()
