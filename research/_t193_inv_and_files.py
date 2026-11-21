from pathlib import Path
# inventory plan/army_group lines
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
for i,l in enumerate(inv.read_text(encoding="utf-8").splitlines(),1):
    if any(s in l for s in ("army_group", "world.plans", "plan_id", "formation")):
        print(f"{i:4d}|{l}")
print("---files---")
for pat in ["research/t188*", "research/*plan*", "research/*army_group*", "calling/*order*", "calling/*plan*", "calling/*army*"]:
    pass
root = Path(".")
hits = []
for p in list(root.glob("research/t188*")) + list(root.glob("research/*plan*")) + list(root.glob("calling/*plan*")) + list(root.glob("docs/*PLAN*")) + list(root.glob("docs/*LAND*")):
    hits.append(str(p))
print("\n".join(hits[:80]))
