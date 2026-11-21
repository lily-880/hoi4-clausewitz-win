from pathlib import Path
import json, re
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md").read_text(encoding="utf-8")
print("=== 已验证 ===")
for ln in inv.splitlines():
    if "| 已验证 |" in ln:
        print(ln)

sch = json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
defs = sch.get("$defs") or sch.get("definitions") or {}
for name in ("Shortages","EquipmentShortage","ManpowerShortage","MissingDivisions","Feedback","Meta","Policy"):
    if name in defs:
        print("====", name, "====")
        print(json.dumps(defs[name], ensure_ascii=False, indent=2)[:2000])
world = sch.get("properties",{}).get("world",{}).get("properties",{})
if "shortages" in world:
    print("==== world.shortages ====")
    print(json.dumps(world["shortages"], ensure_ascii=False, indent=2)[:1500])
meta = sch.get("properties",{}).get("meta",{})
print("==== meta ====")
print(json.dumps(meta, ensure_ascii=False, indent=2)[:1500])
