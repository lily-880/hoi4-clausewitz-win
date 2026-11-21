from pathlib import Path
t = Path("calling/input_capture_live.py").read_text(encoding="utf-8")
for i, l in enumerate(t.splitlines(), 1):
    if any(s in l for s in ("CController", "controller", "province", "def ", "owner", "tag")):
        print(f"{i:4d}|{l[:200]}")
print("======= province mentions in gamestate =======")
t = Path("calling/gamestate.py").read_text(encoding="utf-8")
for i, l in enumerate(t.splitlines(), 1):
    if "CController" in l or "province" in l.lower() and ("def " in l or "CONTROLLER" in l or "0x" in l):
        print(f"{i:4d}|{l[:200]}")
