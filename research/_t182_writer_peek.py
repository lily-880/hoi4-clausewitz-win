import json
from pathlib import Path
p=Path("research/t165_army_secondary_writer.json")
print("size", p.stat().st_size)
d=json.loads(p.read_text(encoding="utf-8"))
print(type(d), d.keys() if isinstance(d,dict) else "list"+str(len(d)))
if isinstance(d,dict):
    for k,v in d.items():
        if k in ("ins","code","ops"): 
            print(k, "len", len(v) if hasattr(v,"__len__") else v)
            continue
        print("KEY", k, "=>", str(v)[:400])
# tokens
def walk(o,path=""):
    if isinstance(o, dict):
        if "token" in o or "named" in str(o.keys()).lower() or "edx" in str(o).lower() and "0x" in str(o):
            s=json.dumps(o, ensure_ascii=False)
            if any(k in s.lower() for k in ("combat","order","path","supply","isolated","4ced","token","610","200")):
                if len(s)<500:
                    print(path, s)
        for k,v in o.items():
            walk(v, path+"/"+str(k)[:40])
    elif isinstance(o, list):
        # if list of asm
        if o and isinstance(o[0], dict) and "asm" in o[0]:
            for item in o:
                a=item.get("asm","")
                if any(k in a for k in ("0x4ced","combat","0x610","0x200","edx, 0x")):
                    print(item)
        else:
            for i,v in enumerate(o[:5]):
                walk(v, path+f"[{i}]")
            if len(o)>5:
                # search all
                for v in o:
                    sv=json.dumps(v) if not isinstance(v,str) else v
                    if any(k in sv.lower() for k in ("combat","order","isolated","path","4ced","land_")):
                        print(sv[:300])
walk(d)
