from pathlib import Path
# can_execute offset near 0x10d1a10
lines=Path("research/_t188_clip_orderinstance_writer_0x10d1450.txt").read_text(encoding="utf-8").splitlines()
# print 0x10d19f0-0x10d1a80 window
for l in lines:
    if l.startswith("0x10d19") or l.startswith("0x10d1a") or l.startswith("0x10d1b"):
        print(l)

# t192 test sha pin
t=Path("research/test_t192_input_army_leader.py").read_text(encoding="utf-8")
for i,l in enumerate(t.splitlines(),1):
    if "SHA" in l or "read_bytes" in l or "hexdigest" in l or "sha256" in l:
        print(f"T192TEST {i}:{l}")
