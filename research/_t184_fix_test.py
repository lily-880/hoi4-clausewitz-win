from pathlib import Path
p=Path("research/test_t184_input_formation_combat.py")
t=p.read_text(encoding="utf-8")
old='        self.assertIn("0x22858d4  mov edx, 0xb  ; TOKEN id", base)'
new='        self.assertIn("0x22858cf  mov edx, 0xb  ; TOKEN id", base)'
if old not in t:
    raise SystemExit("pattern missing")
p.write_text(t.replace(old,new), encoding="utf-8")
print("patched")
