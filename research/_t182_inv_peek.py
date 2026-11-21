from pathlib import Path
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
text = inv.read_text(encoding="utf-8")
keys = ("in_combat","order","supply","formation","assigned_to","combat","path","idle")
for i,l in enumerate(text.splitlines(),1):
    if any(k in l for k in keys) or "world.own_units" in l or "world.leaders" in l or "world.armies" in l or "world.combats" in l:
        print(f"{i}:{l}")
print("===== prior research hits =====")
root=Path("research")
for p in sorted(root.glob("*")):
    name=p.name.lower()
    if any(k in name for k in ("combat","order","supply","formation","assigned","leader","idle","path")):
        print(p.name, p.stat().st_size)
