from pathlib import Path
import json
# t180 xrefs script river parts
t=Path("research/_t180_xrefs.py").read_text(encoding="utf-8")
for i,l in enumerate(t.splitlines(),1):
    if any(k in l.lower() for k in ("river","crossing","2b494b0","xref")):
        print(f"{i}:{l}")
print("===== t180_adjacency_xrefs keys =====")
x=json.loads(Path("research/t180_adjacency_xrefs.json").read_text(encoding="utf-8"))
print(type(x), x.keys() if isinstance(x,dict) else len(x))
if isinstance(x,dict):
    for k,v in x.items():
        sv=json.dumps(v, ensure_ascii=False) if not isinstance(v, (str,int)) else v
        print("KEY", k, "=>", (sv[:400] if isinstance(sv,str) else sv))
# t179 strings containing river/crossing
s=json.loads(Path("research/t179_adjacency_strings.json").read_text(encoding="utf-8"))
print("===== t179 adjacency strings type", type(s), (list(s)[:20] if isinstance(s,dict) else "list"+str(len(s))))
items = s if isinstance(s,list) else s.get("strings") or s.get("hits") or s
if isinstance(s,dict):
    print("dict keys", s.keys())
# find river_crossing
def walk(o):
    if isinstance(o, dict):
        text=json.dumps(o, ensure_ascii=False)
        if "river" in text.lower() or "cross" in text.lower():
            # print compact
            if "s" in o and isinstance(o["s"], str) and ("river" in o["s"].lower() or "cross" in o["s"].lower()):
                print(o)
            for v in o.values():
                walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
    elif isinstance(o, str) and ("river" in o.lower() or "cross" in o.lower()):
        print("STR", o[:200])
walk(s)
