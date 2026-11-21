from pathlib import Path
p = Path(r"C:\Users\Lenovo\agent-tools\t197_parts_py.txt")
lines = p.read_text(encoding="utf-8").splitlines()
# print from line 180
print("\n".join(lines[180:]))
