import json,re
from pathlib import Path
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
keys=("crisis","alert","encircl","out_of_supply","org_collapse","spotted","confidence","visibility","fog","intel_level","recon","detected")
for i in mp:
    n=i["name"].lower()
    if any(k in n for k in keys):
        print(f"0x{i['token']:x} {i['name']}")
