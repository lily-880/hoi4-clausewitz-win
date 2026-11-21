from pathlib import Path
t = Path("research/test_t186_input_wars.py").read_text(encoding="utf-8")
for i,l in enumerate(t.splitlines(),1):
    if any(s in l for s in ("SHA", "sha256", "verified", "inventory", "INV", "frozen", "pin")):
        print(f"{i:4d}|{l}")
print("--- snippet around inventory test ---")
lines=t.splitlines()
for i,l in enumerate(lines):
    if "def test_" in l and "inv" in l.lower() or "sha" in l.lower() and "def " in l:
        print("\n".join(f"{j+1:4d}|{lines[j]}" for j in range(i, min(len(lines), i+40))) )
