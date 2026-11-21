from pathlib import Path
import json

# t192 bind of CArmyGroupCommand
bind = json.loads(Path("research/t192_bind_cmds.json").read_text(encoding="utf-8"))
print("===== t192_bind keys =====")
print(bind.keys() if isinstance(bind, dict) else type(bind))
if isinstance(bind, dict):
    # print army group related
    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k,v in o.items():
                if any(s in str(k).lower() for s in ("armygroup","army_group","front","orderinstance","setarmyleader","ordergroup")) or any(s in str(k) for s in ("CArmyGroup","CFront","COrder")):
                    print(prefix+str(k), ":", json.dumps(v, ensure_ascii=False)[:500] if not isinstance(v, (dict,list)) or True else "")
                    if isinstance(v, (dict, list)) and "CArmyGroup" in str(k):
                        print(json.dumps(v, ensure_ascii=False, indent=2)[:2000])
                elif isinstance(v, dict) and any(s in str(k).lower() for s in ("cmd","bind","rtti")):
                    walk(v, prefix+str(k)+".")
    # just dump compact army group / front
    s = json.dumps(bind, ensure_ascii=False, indent=2)
    for i,l in enumerate(s.splitlines(),1):
        if any(x in l for x in ("CArmyGroup", "CFront", "CNewFront", "COrderInstance", "frontline", "marshal")):
            print(l)
            if i>0 and len(s.splitlines())<200:
                pass
print("\n===== full bind if small =====")
print("len", len(json.dumps(bind)))
if len(json.dumps(bind)) < 20000:
    print(json.dumps(bind, ensure_ascii=False, indent=2))
