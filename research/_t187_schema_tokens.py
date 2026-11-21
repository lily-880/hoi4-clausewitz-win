import json,re
from pathlib import Path

schema=json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))

def find_key(obj, key, path=""):
    hits=[]
    if isinstance(obj, dict):
        for k,v in obj.items():
            p=f"{path}.{k}" if path else k
            if key.lower() in k.lower():
                hits.append((p,v if not isinstance(v,(dict,list)) or len(json.dumps(v,ensure_ascii=False))<2000 else "big"))
            hits += find_key(v, key, p)
    elif isinstance(obj, list):
        for i,v in enumerate(obj[:8]):
            hits += find_key(v, key, f"{path}[]")
    return hits

for key in ("speed","pause","paused","Plan","Crisis","Visibility","spotted","confidence"):
    hits=find_key(schema, key)
    print(f"\n===== schema {key} n={len(hits)} =====")
    for p,v in hits[:8]:
        print(p)
        if not isinstance(v,str):
            print(json.dumps(v, indent=2, ensure_ascii=False)[:1200])
        else:
            print(v[:400])

mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
print("\n===== pause/speed/plan/crisis/fog tokens =====")
for i in mp:
    n=i["name"]
    if n in ("pause","paused","is_paused","unpause","game_speed","speed","game_paused") or "pause" in n or n in ("front","offensive_line","fallback_line","garrison","area_defense","plan","planning","is_executing","execute") or "crisis" in n or "encircled" in n or n in ("isolated","out_of_supply","spotted","visibility","intel","fog","fog_of_war","confidence") or "plan" in n:
        if any(k in n for k in ("pause","speed","plan","front","crisis","encirc","spotted","visibility","fog","intel","confidence","offensive","fallback","garrison","area_defense","execute")):
            print(hex(i["token"]), n)
