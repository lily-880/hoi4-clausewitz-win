from pathlib import Path
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md").read_text(encoding="utf-8")
keys = ("plan", "crisis", "crises", "visible", "visibility", "fog", "spotted", "confidence", "damaged", "building", "front", "order")
for ln in inv.splitlines():
    low = ln.lower()
    if any(k in low for k in keys) or any(k in ln for k in ("计划","危机","可见","迷雾","受损","建筑","前线","置信")):
        print(ln)
print("--- schema ---")
import json
sch = json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
# print plan/crisis/visibility/building related defs
text = json.dumps(sch, ensure_ascii=False, indent=2)
# too long; extract keys
def walk(obj, prefix=""):
    if isinstance(obj, dict):
        if "properties" in obj and prefix:
            pass
        for k,v in obj.items():
            if k in ("properties","$defs","definitions","items","allOf","anyOf","oneOf","then","else","if"):
                walk(v, prefix)
            elif k not in ("description","type","enum","required","additionalProperties","minItems","maxItems","minimum","maximum","default","$ref","title","examples","pattern","format","const"):
                if any(s in (prefix+"."+k).lower() for s in ("plan","crisis","visib","fog","spot","confid","damage","building","front")):
                    print(prefix+"."+k)
                walk(v, prefix+"."+k if prefix else k)
            else:
                walk(v, prefix)
walk(sch)
