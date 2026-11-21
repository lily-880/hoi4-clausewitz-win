from pathlib import Path

# --- move_order.py constants ---
p = Path("calling/move_order.py")
t = p.read_text(encoding="utf-8")
old = '''FACTORY_RVA = 0x13FB000
FACTORY_IDX = 1402
ACTION_ISVALID_RVA = 0x12C2CA0
MOVE_VT = 0x2A2C790
ACTION_VT = 0x2A1F648
ARMY_VT = 0x29D6D68
'''
new = '''# 1.19.5.0.7c6c rebase (t191): same factory idx / size 0x88, RVAs slid ~+0x70;
# vtables from RTTI; factory from live TYPEID_FACTORY_TABLE idx 1402.
FACTORY_RVA = 0x13FB070
FACTORY_IDX = 1402
ACTION_ISVALID_RVA = 0x12C2D10  # CUnitMoveAction vt+0x50; 1.19.4 was 0x12C2CA0
MOVE_VT = 0x2A2CDE0
ACTION_VT = 0x2A1FAC8
ARMY_VT = 0x29D6D98  # matches offsets_input_windows_1.19.5.json CArmy
'''
if old not in t:
    raise SystemExit("move_order.py constants block not found exactly")
p.write_text(t.replace(old, new, 1), encoding="utf-8")

# also refresh the module docstring factory rva mention
t = p.read_text(encoding="utf-8")
t = t.replace("Factory 0x13FB000 (idx 1402)", "Factory 0x13FB070 (idx 1402, 1.19.5)")
t = t.replace("IsValid: action RVA 0x12C2CA0", "IsValid: action RVA 0x12C2D10")
p.write_text(t, encoding="utf-8")

# --- post_abi.py FN_CMD_QUEUE_POST ---
p = Path("calling/post_abi.py")
t = p.read_text(encoding="utf-8")
old = "FN_CMD_QUEUE_POST = 0x22C41E0"
new = "FN_CMD_QUEUE_POST = 0x22C4250  # 1.19.5.0.7c6c; 1.19.4 was 0x22C41E0. Confirmed: [session+0x40].vt+0x28 sink, gates +0x725/+0x726/+0x6cc"
if old not in t:
    raise SystemExit("post_abi FN_CMD_QUEUE_POST not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")

# optional sink/drain comments for accuracy (used as documentation; live vt read is source of truth)
t = p.read_text(encoding="utf-8")
t = t.replace("FN_CMD_QUEUE_POST_SINK_DUMMY = 0x23F5CD0  # CDummyServer vt+0x28",
              "FN_CMD_QUEUE_POST_SINK_DUMMY = 0x23F5D40  # CDummyServer vt+0x28 (1.19.5)")
t = t.replace("FN_CMD_QUEUE_DRAIN_DUMMY = 0x23F64E0  # CDummyServer vt+0x30",
              "FN_CMD_QUEUE_DRAIN_DUMMY = 0x23F6550  # CDummyServer vt+0x30 (1.19.5)")
t = t.replace("FN_SESSION_UPDATE = 0x22C6410",
              "FN_SESSION_UPDATE = 0x22C6480  # 1.19.5")
t = t.replace("CDummyServer_VT = 0x2BCB040",
              "CDummyServer_VT = 0x2BCBEA0  # 1.19.5 RTTI; live server matches")
p.write_text(t, encoding="utf-8")

# verify imports
import sys
sys.path.insert(0, "calling")
# fresh import by exec? already may be cached if we imported earlier in this process — new process below
print("patched ok")
print(Path("calling/move_order.py").read_text(encoding="utf-8").splitlines()[18:27])
print("---")
for i,l in enumerate(Path("calling/post_abi.py").read_text(encoding="utf-8").splitlines(),1):
    if "FN_CMD_QUEUE_POST" in l or "CDummyServer_VT" in l or "SINK_DUMMY" in l or "DRAIN_DUMMY" in l or "SESSION_UPDATE" in l:
        print(f"{i}:{l}")
