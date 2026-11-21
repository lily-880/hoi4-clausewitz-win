from pathlib import Path, PureWindowsPath
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
text = inv.read_text(encoding="utf-8")
for i,l in enumerate(text.splitlines(),1):
    if any(k in l for k in ("neighbors","has_river","邻接","渡河","已验证","未验证","表")):
        if any(k in l for k in ("neighbors","has_river","邻接","渡河","字段名","已验证/","116","14 表","41","75")) or "world.provinces" in l:
            print(f"{i}:{l}")
print("--- all province lines ---")
for i,l in enumerate(text.splitlines(),1):
    if "world.provinces" in l or "has_river" in l or "neighbors" in l:
        print(f"{i}:{l}")
print("sha file exists", inv.exists(), "bytes", inv.stat().st_size)
