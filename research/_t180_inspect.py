from pathlib import Path
import json, pprint
s=json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
prov=s["$defs"]["Province"]
pprint.pp(prov)
o=json.loads(Path("calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8-sig"))
print("=== offset top keys ===")
print(list(o.keys()))
for k in ("fields","offsets","notes"):
    if k in o:
        print(k, "len", len(o[k]) if hasattr(o[k],"__len__") else type(o[k]))
if "fields" in o:
    keys=list(o["fields"].keys())
    print("last fields:", keys[-15:])
    for k in keys[-8:]:
        pprint.pp({k:o["fields"][k]})
else:
    # maybe nested differently
    def show(obj, prefix, depth=0):
        if depth>2: return
        if isinstance(obj, dict):
            for i,k in enumerate(obj):
                if i>30 and depth==0:
                    print(prefix, "... total", len(obj))
                    break
                v=obj[k]
                if isinstance(v, dict) and depth<1:
                    print(prefix+k, "dict", list(v.keys())[:12])
                    show(v, prefix+k+".", depth+1)
                else:
                    sv=repr(v)
                    print(prefix+k, sv[:200])
    show(o, "")
