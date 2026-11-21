# -*- coding: utf-8 -*-
from pathlib import Path
p = Path("calling/offsets.py")
text = p.read_text(encoding="utf-8")
needle = '    "CA_DIV_TEMPLATE": 0x3B8,  # CReferencedDivisionTemplate*\n'
insert = needle + '''    # Live-proven 2026-11-14 HOI4 1.19.4 Windows, ETH opening 21/21, pid 22604, paused.
    # Division scalars below are i32 Clausewitz FIXED (value/100000) unless noted.
    # CArmy object size / heap stride is 0x690.
    "CA_PATH": 0x200,  # CPdxArray<u32> movement path; empty (null or size 0) at this idle snapshot
    "CA_STRENGTH_420_RAW": 0x420,  # Historical full-HP equality did NOT prove max. On1.19.5 this is CURRENT HP; max uses primary vtable+0x108, see input version profile.
    "CA_ORGANIZATION": 0x428,  # FIXED current org; 21/21 = 0.95 * template max_org at this opening snapshot
    "CA_EQUIPMENT_RATIO": 0x468,  # FIXED; 21/21 = start_equipment_factor. An identical copy exists at +0x5A8; not registered until the two diverge.
    "CA_MANPOWER": 0x4F0,  # FIXED; 21/21 = template manpower 4000/5000/6000. current vs max not split (no casualties yet)
    "CA_EXPERIENCE": 0x5B8,  # FIXED; 21/21 = start_experience_factor
    "CA_LEADER_ID": 0x564,  # i32; -1 if none; 68853-68857 for the five OOB officers
    "CA_OFFICER": 0x568,  # SUnitOfficerData*; non-null iff an officer is present
    "CA_OBJECT_SIZE": 0x690,  # live allocation stride between CArmy objects
'''
if "CA_ORGANIZATION" in text:
    print("ALREADY_PATCHED")
elif needle not in text:
    print("NEEDLE_MISSING")
else:
    p.write_text(text.replace(needle, insert, 1), encoding="utf-8")
    print("PATCHED")
