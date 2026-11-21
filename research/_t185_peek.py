import json,re
from pathlib import Path

# remaining CLandCombatant tokens and nearby mem
text=Path("research/_t184_clip_landcombatant_writer_0x134d5f0.txt").read_text(encoding="utf-8")
print("===== landcombatant clip all TOKEN / mem =====")
for ln in text.splitlines():
    if "TOKEN" in ln or re.search(r"\[(rbx|rdi|rsi|rbp|r1[0-5]|r14) \+", ln) or "lea r8" in ln or "call 0x228" in ln or "call 0x147" in ln:
        print(ln)
print("lines", len(text.splitlines()), "tail:")
print("\n".join(text.splitlines()[-15:]))

# tokens of interest
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
name2={i["name"]:i["token"] for i in mp}
for n in ("in_supply","isolated","is_isolated","has_supply","supply_status","is_in_supply","out_of_supply","encircled","is_encircled","cut_off"):
    if n in name2:
        print("TOKEN", n, hex(name2[n]))
print("fuzzy:")
for i in mp:
    if any(s in i["name"] for s in ("in_supply","isolated","encircl","cut_off","is_supplied","has_supply","supply_isolated","unsupplied")):
        print(hex(i["token"]), i["name"])
