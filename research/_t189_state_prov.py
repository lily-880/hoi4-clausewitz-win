import json
from pathlib import Path
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
for i in mp:
    n=i["name"].lower()
    if "confiden" in n or n in ("visible","visibility","spotted","detected","intel","army_intel") or "fog" in n:
        print(hex(i["token"]), i["name"])

# find state province array from t169 scripts / offsets
for p in list(Path("research").glob("t169*.py"))+list(Path("research").glob("t168*.py"))+[Path("calling/offsets.py"), Path("calling/input_loaded_fields.py")]:
    if not p.exists(): continue
    t=p.read_text(encoding="utf-8", errors="replace")
    hits=[]
    for i,ln in enumerate(t.splitlines(),1):
        if any(s in ln.lower() for s in ("state+","cstate","co_states","provinces","+0x190","st+0x","cs_prov")):
            if "province" in ln.lower() or "0x190" in ln or "STATES" in ln or "CState" in ln:
                hits.append(f"{i}:{ln[:200]}")
    if hits:
        print("====", p.name, "====")
        print("\n".join(hits[:25]))
