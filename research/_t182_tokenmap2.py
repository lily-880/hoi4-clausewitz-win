import json,re
from pathlib import Path
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
print("list len", len(mp), "first", mp[0])
# build maps
id2name={}; name2id={}
for item in mp:
    if isinstance(item, dict):
        tok=item.get("token") or item.get("id") or item.get("tok") or item.get("value")
        name=item.get("name") or item.get("s") or item.get("string") or item.get("key")
        if tok is None or name is None:
            if len(id2name)==0:
                print("dict keys", item.keys(), "item", item)
            continue
        if isinstance(tok,str):
            tok=int(tok,16) if tok.startswith("0x") else int(tok)
        id2name[tok]=name
        name2id[name]=tok
    elif isinstance(item, (list,tuple)) and len(item)>=2:
        a,b=item[0],item[1]
        if isinstance(a,int) and isinstance(b,str):
            id2name[a]=b; name2id[b]=a
        elif isinstance(b,int) and isinstance(a,str):
            id2name[b]=a; name2id[a]=b
    else:
        print("unknown item type", type(item), item)
        break
print("id2name", len(id2name))
toks=[0x4ced,0x4cec,0x4bcc,0x3142,0x354f,0x3904,0x3a43,0x2ecb,0x28a6,0x2f4e,0x4b95,0x36fa,0x2e9a,0x2ee3,0x3bc2,0x335f,0x33ae,0x2ed7,0x34fa,0x2ab3,0x2edb,0x2ee8,0x35ba,0x374c,0x374d,0x374e,0x3041,0x3851,0x2e60,0x336c,0x34f4,0x28b7]
for t in toks:
    print(hex(t), id2name.get(t))
print("----- name search -----")
for n,i in sorted(name2id.items(), key=lambda x:x[0]):
    if any(k in n.lower() for k in ("combat","order","path","supply","isolated","in_supply","land_combat","in_combat","assigned")):
        if n.startswith("N") and "Military" in n: continue
        if "ERROR" in n.upper() and len(n)>40: continue
        print(hex(i), n)
