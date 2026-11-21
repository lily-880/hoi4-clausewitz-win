from pathlib import Path
import json
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md").read_text(encoding="utf-8")
keys = ("crisis","crises","visible","visibility","spotted","confidence","damaged","building","受损","建筑","危机","可见","迷雾","有效等级","额外")
for ln in inv.splitlines():
    if any(k in ln.lower() or k in ln for k in keys):
        print(ln)
sch = json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
defs = sch.get("$defs") or sch.get("definitions") or {}
for name in ("Crisis","VisibleUnit","Building","Province","State"," infra"):
    pass
# find building-related defs
for name, obj in defs.items():
    s = json.dumps(obj, ensure_ascii=False)
    if any(k in name.lower() or k in s.lower() for k in ("building","damage","damaged","level","crisis","visibility","spotted")):
        if name in ("Crisis","VisibleUnit","Building","ProvinceBuildings","StateBuildings","BuildingLevels","Province"):
            print("====", name, "====")
            print(s[:2000])
# also scan required world properties names
world = sch.get("properties",{}).get("world",{}).get("properties",{})
for k,v in world.items():
    if any(s in k.lower() for s in ("crisis","visib","build","province","state")):
        print("world key", k)
