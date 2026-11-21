from pathlib import Path
import json

# t165 supply + formation
for n in ["research/t165_army_manpower_supply.json","research/t165_world_formation_inventory.json"]:
    p=Path(n)
    print("=======", n, p.stat().st_size)
    t=p.read_text(encoding="utf-8")
    print(t[:4000])
    print("----- tail -----")
    print(t[-1500:] if len(t)>4000 else "")

print("======= offsets invalidated / combat-ish keys =====")
off=json.loads(Path("calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8-sig"))
inv=off.get("invalidated_or_unproven") or off.get("evidence")
print("invalidated type", type(off.get("invalidated_or_unproven")))
x=off.get("invalidated_or_unproven")
if isinstance(x, dict):
    for k,v in x.items():
        if any(s in k.lower() or s in str(v).lower() for s in ("combat","order","supply","formation","assigned","idle","path")):
            print(k, ":", str(v)[:300])
    print("all keys", list(x)[:80], "total", len(x))
elif isinstance(x, list):
    for v in x:
        if any(s in str(v).lower() for s in ("combat","order","supply","formation","assigned","idle","path")):
            print(str(v)[:400])

print("======= offset top keys with those words =====")
for k,v in off.items():
    if any(s in k.lower() for s in ("combat","order","supply","formation","assigned","leader","army")):
        print(k, ":", str(v)[:250])
