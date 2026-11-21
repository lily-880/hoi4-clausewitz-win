import json,re
from pathlib import Path

# token map
mp=None
for n in ["research/t163_script_token_map.json","research/t165_script_token_map.json","calling/tables/script_tokens.json"]:
    p=Path(n)
    if p.exists():
        print("found", n, p.stat().st_size)
        mp=json.loads(p.read_text(encoding="utf-8"))
        break
if mp is None:
    # search
    for p in Path("research").glob("*token*"):
        print("candidate", p, p.stat().st_size)
    raise SystemExit("no token map")

print("map type", type(mp), list(mp)[:12] if isinstance(mp,dict) else len(mp))

def lookup(tok):
    # tok int
    keys=[tok, hex(tok), hex(tok)[2:], str(tok), format(tok,"x"), format(tok,"04x")]
    if isinstance(mp, dict):
        # maybe {hex:name} or {name:hex} or list
        for k in keys:
            if k in mp: return mp[k]
            if k.lower() in mp: return mp[k.lower()]
        # invert if values are ints
        # try 'tokens' sub
        for subk in ("tokens","map","id_to_name","by_id"):
            if subk in mp and isinstance(mp[subk], dict):
                for k in keys:
                    if k in mp[subk]: return mp[subk][k]
        # scan first item
    return None

# print map structure sample
if isinstance(mp, dict):
    items=list(mp.items())[:5]
    print("sample items", items)
    # if values look like names
    # build id->name
    id2name={}
    def add(k,v):
        # k token, v name or vice versa
        def to_int(x):
            if isinstance(x,int): return x
            if isinstance(x,str):
                try:
                    return int(x,16) if x.startswith("0x") or re.fullmatch(r"[0-9a-fA-F]+",x) and not re.fullmatch(r"[0-9]+",x) and len(x)<=4 else int(x,0) if x.startswith("0x") else (int(x) if x.isdigit() else None)
                except: return None
            return None
        ki,vi=to_int(k),to_int(v)
        if ki is not None and isinstance(v,str) and not v.isdigit():
            id2name[ki]=v
        elif vi is not None and isinstance(k,str) and not k.isdigit():
            id2name[vi]=k
    if "tokens" in mp:
        inner=mp["tokens"]
        if isinstance(inner, dict):
            for k,v in inner.items(): add(k,v)
        elif isinstance(inner, list):
            print("tokens list sample", inner[:3])
    else:
        for k,v in mp.items():
            if isinstance(v,(dict,list)): continue
            add(k,v)
    print("id2name size", len(id2name), "sample", list(id2name.items())[:8])
    toks=[0x4ced,0x4cec,0x4bcc,0x3142,0x354f,0x3904,0x3a43,0x2ecb,0x28a6,0x2f4e,0x4b95,0x36fa,0x2e9a,0x2ee3,0x3bc2,0x335f,0x33ae,0x2ed7,0x34fa,0x2ab3,0x2edb,0x2ee8,0x35ba,0x374c,0x374d,0x374e,0x3041,0x3851,0x2e60,0x336c,0x34f4,0x28b7]
    for t in toks:
        print(hex(t), id2name.get(t) or lookup(t))
    # search names
    hits=[]
    for i,n in id2name.items():
        if any(k in n.lower() for k in ("combat","order","path","supply","isolated","in_supply","idle","move")):
            hits.append((hex(i),n))
    print("name hits", hits[:80], "count", len(hits))
