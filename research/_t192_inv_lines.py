from pathlib import Path
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
for i,l in enumerate(inv.read_text(encoding="utf-8").splitlines(),1):
    if any(s in l for s in ("formation", "world.armies", "world.army_groups", "assigned_to", "leaders.")):
        print(f"{i:4d}|{l}")
