import json
from pathlib import Path
d=json.loads(Path("research/t165_province_theatre_code.json").read_text(encoding="utf-8"))
tw=d["theatre_write"]
print("theatre_write keys", list(tw) if isinstance(tw, dict) else type(tw))
if isinstance(tw, dict):
    for k,v in tw.items():
        if k=="code" and isinstance(v, list):
            print("code lines", len(v))
            # print token-bearing or first/last
            for item in v:
                s=item if isinstance(item,str) else json.dumps(item)
                if "TOKEN" in s or "0xf815" in s or "edx" in s.lower():
                    print(s[:250])
        else:
            print(k, json.dumps(v, ensure_ascii=False)[:400] if not isinstance(v,list) else f"list[{len(v)}]")
