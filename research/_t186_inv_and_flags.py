import sys,os,json,re
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, tag_for_index
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

# inventory war lines
INV=Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
text=INV.read_text(encoding="utf-8")
for i,ln in enumerate(text.splitlines(),1):
    if "wars" in ln.lower() or "战争" in ln:
        print(f"{i}: {ln}")

# front_invalid token
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
for i in mp:
    n=i["name"]
    if "invalid" in n or "front" in n and "war" in n or n in ("front_invalidated","invalidated","is_front_invalid","fronts_invalid"):
        print("tok", hex(i["token"]), n)

p=Proc(find_pid("hoi4.exe"))
pe=PE(p.image_path)
try:
    wp=0x26c70b635d0
    raw=p.try_read(wp, 0x180) or b""
    print("bytes 0x48-0x50", raw[0x48:0x50].hex())
    print("u8_48", raw[0x48], "u8_49", raw[0x49], "u8_4a", raw[0x4a], "u8_4b", raw[0x4b])
    print("first", p.i32(wp+0x10), tag_for_index(p.i32(wp+0x10)), "second", p.i32(wp+0x14), tag_for_index(p.i32(wp+0x14)))
    print("tick20", p.i32(wp+0x20), "tick38", p.i32(wp+0x38))
finally:
    p.close()
