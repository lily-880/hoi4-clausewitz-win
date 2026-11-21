import json, os
from pathlib import Path

# campaign tick/speed if we can find helpers already used
import sys
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session
import inspect, gamestate
print("gamestate funcs:", [n for n,v in inspect.getmembers(gamestate, inspect.isfunction)])

# list relevant prior artifacts
keys=["formation","assigned","is_assigned","combat","commandlist","theatre","marshal","leader"]
root=Path("research")
hits=[]
for p in sorted(root.glob("t16*.json"))+sorted(root.glob("t165*"))+sorted(root.glob("*formation*"))+sorted(root.glob("*assigned*"))+sorted(root.glob("*leader*")):
    hits.append(str(p))
print("files:")
for p in sorted(set(Path(h).name for h in hits)):
    print(" ", p)

# token
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2={i["token"]:i["name"] for i in mp}
name2={i["name"]:i for i in mp}
for n in ["is_assigned","assigned_to","assigned","assignment","army_group","theatre","theater","field_marshal","commander","leader","in_combat","in_supply","isolated","supply_ratio","army_current_supply_ratio","IsInCombat","combat"]:
    if n in name2:
        print("TOKEN", n, hex(name2[n]["token"]), "reg", name2[n].get("registration_rva"))

# fuzzy
for i in mp:
    nm=i["name"]
    if any(s in nm for s in ("assign", "theatre", "theater", "army_group", "field_marshal", "in_combat", "in_supply", "isolated", "commandlist", "combat_id")):
        print(hex(i["token"]), nm, "reg", i.get("registration_rva"))
