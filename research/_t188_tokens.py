import json,re
from pathlib import Path
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
keys=("plan","front","offensive","garrison","area_defense","fallback","spearhead","battle_plan","order_instance","executing","vertex","axis","frontline","invasion","defence","defense","crisis","encircl","spotted","confidence","visibility","fog","damaged")
hits=[]
for i in mp:
    n=i["name"].lower()
    if any(k in n for k in keys):
        hits.append((i["token"], i["name"]))
print("token hits", len(hits))
for tok,name in hits:
    if any(k in name.lower() for k in ("plan","frontline","offensive_line","garrison","area_def","fallback","spearhead","battle_plan","order_inst","execut","vertex","axis","crisis","encircl","spotted","confidence","visibility","fog_of","damaged","building_level","damage")):
        print(f"0x{tok:x} {tok} {name}")
