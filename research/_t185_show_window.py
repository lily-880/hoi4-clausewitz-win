from pathlib import Path
lines=Path("research/_t185_clip_plandcombat_assert_0x11105b0.txt").read_text(encoding="utf-8").splitlines()
print("--- 0x1110d40-0x1110e80 ---")
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0x1110d40<=addr<=0x1110e80:
        print(ln)
print("\n--- 0x1110c80-0x1110d40 ---")
for ln in lines:
    addr=int(ln.split()[0],16)
    if 0x1110c80<=addr<=0x1110d40:
        print(ln)
# also search for 0xc52e90 and land-combat-like calls
print("\n--- calls and rdi/r14 loads ---")
for ln in lines:
    if "call 0x" in ln or "0x20c" in ln or "pLand" in ln or "0xc4f" in ln or "0xc52" in ln:
        print(ln)
