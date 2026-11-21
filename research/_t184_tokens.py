import json,sys
from pathlib import Path

# theatre/group related prior artifacts and token names we'll need
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
name2={i["name"]:i for i in mp}
want=["theatre","theatres","theater_group","theater_group_index","field_marshal_group","orders_group","army_group","army","armies","unit","units","leader","commander","id","name","province","order_group","orders"]
for n in want:
    if n in name2:
        print("TOKEN", n, hex(name2[n]["token"]))

print("--- fuzzy ---")
for i in mp:
    n=i["name"]
    if any(s==n or n.endswith("_id") and any(k in n for k in ("army","theatre","theater","group","unit","combat","order")) for s in ("theatre","theater_group","field_marshal_group","orders_group","army_group","army_id","unit_ids")):
        if any(k in n for k in ("theatre","theater","army_group","orders_group","field_marshal","army_id","unit_id","combat","group_id")):
            print(hex(i["token"]), n)

print("\n--- t165 theatre code keys ---")
for fn in ["research/t165_province_theatre_code.json","research/t165_world_formation_inventory.json"]:
    if Path(fn).exists():
        d=json.loads(Path(fn).read_text(encoding="utf-8"))
        print(fn, list(d)[:20] if isinstance(d,dict) else type(d))
