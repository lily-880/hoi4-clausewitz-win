import json
from pathlib import Path

# leader field layout samples
for fn in ["research/t163_leader_fields.json","research/t163_army_leaders.json","research/t163_character_leader_links.json","research/t163_unitleader_base_writer.json"]:
    d=json.loads(Path(fn).read_text(encoding="utf-8"))
    print("====", fn)
    if "leaders" in d:
        L=d["leaders"]
        print("n", len(L), "keys0", list(L[0].keys()) if L else None)
        # print compact first 2
        for item in L[:2]:
            slim={k:v for k,v in item.items() if not (isinstance(v,(str,bytes)) and len(str(v))>200)}
            print(json.dumps(slim, ensure_ascii=False)[:1500])
            print("---")
    elif "code" in d:
        print("function", d.get("function"), "end", d.get("end"), "code lines", len(d["code"]) if isinstance(d["code"],list) else type(d["code"]))
        code=d["code"]
        if isinstance(code, list):
            text="\n".join(code if isinstance(code[0],str) else json.dumps(c) for c in code[:80])
            print(text[:2500])
        elif isinstance(code, str):
            print(code[:2500])
    else:
        print("keys", list(d.keys())[:30])
        print(json.dumps({k:d[k] for k in list(d)[:8]}, default=str, ensure_ascii=False)[:1500])
