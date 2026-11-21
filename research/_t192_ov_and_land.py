import json
from pathlib import Path

# offsets_verified and land post json snippets
ov = json.loads(Path("calling/offsets_verified.json").read_text(encoding="utf-8"))

def find_keys(obj, pred, prefix=""):
    hits = []
    if isinstance(obj, dict):
        for k,v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if pred(key, v):
                hits.append(key)
            hits += find_keys(v, pred, key)
    elif isinstance(obj, list) and obj and not isinstance(obj[0], (dict, list)):
        return hits
    elif isinstance(obj, list):
        for i,v in enumerate(obj[:50]):
            hits += find_keys(v, pred, f"{prefix}[{i}]")
    return hits

def pred(k,v):
    s = k.lower()
    return any(x in s for x in ("ordergroup", "setarmyleader", "armygroupcommand", "handle_type", "theatre", "leader"))

keys = find_keys(ov, pred)
print("offsets_verified interesting keys", len(keys))
for k in keys[:80]:
    # print short value
    parts = k.split(".")
    cur = ov
    try:
        for p in parts:
            if p.startswith("[") and p.endswith("]"):
                cur = cur[int(p[1:-1])]
            else:
                cur = cur[p]
        val = cur if not isinstance(cur, (dict, list)) else (type(cur).__name__ + " " + str(len(cur)))
        print(f"  {k} = {val}")
    except Exception as e:
        print(f"  {k} ERR {e}")

print("======= search land_post_2dg for COrderGroupCommand =====")
# use ijson-like simple line scan
p = Path("calling/_land_post_2dg.json")
# file is 550k, ok to load? 550934 bytes - fine
# might be slow; try
text = p.read_text(encoding="utf-8", errors="replace")
i = text.find("COrderGroupCommand")
print("first idx", i)
if i>=0:
    print(text[i:i+2000][:2000])
