import json,re
from pathlib import Path

# schema wars
schema=json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))

def walk(obj, path=""):
    if isinstance(obj, dict):
        if "wars" in path.split(".")[-1:] or path.endswith("wars") or "War" in str(obj.get("title","")) or path.endswith("war"):
            yield path, obj
        for k,v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i,v in enumerate(obj[:3]):
            yield from walk(v, f"{path}[]")

# print wars-related schema nodes
s=json.dumps(schema, ensure_ascii=False)
# find wars
idx=s.lower().find("wars")
print("schema has wars?", "wars" in s.lower())

# recurse properties
def find_key(obj, key, path=""):
    hits=[]
    if isinstance(obj, dict):
        for k,v in obj.items():
            p=f"{path}.{k}" if path else k
            if k.lower()==key.lower() or key.lower() in k.lower():
                hits.append((p,v if not isinstance(v, (dict,list)) else (v if isinstance(v, dict) and len(json.dumps(v))<2000 else {ik: ('...' if isinstance(iv,(dict,list)) else iv) for ik,iv in (v.items() if isinstance(v,dict) else [])})))
            hits += find_key(v, key, p)
    elif isinstance(obj, list):
        for i,v in enumerate(obj[:8]):
            hits += find_key(v, key, f"{path}[]")
    return hits

for key in ("wars","War","front_invalidated","pause","paused"):
    hits=find_key(schema, key)
    print(f"\n===== key {key} n={len(hits)} =====")
    for p,v in hits[:8]:
        print(p)
        if isinstance(v, dict):
            print(json.dumps(v, indent=2, ensure_ascii=False)[:1500])
        else:
            print(v)

# token map war-ish
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
print("\n===== war tokens =====")
for i in mp:
    n=i["name"]
    if n in ("war","wars","at_war","is_at_war","has_war","war_name","start_date","attacker","defender","call_ally","peace","armistice","surrender","puppet","truce","ceasefire") or n.startswith("war_") or "front_invalid" in n or n in ("enemies","allies"):
        print(hex(i["token"]), n)

# previous research mentions
print("\n===== prior research files =====")
for p in sorted(Path("research").glob("*war*")):
    print(p)
