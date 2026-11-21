# research/_t191_write_delivery.py — freeze older SHA pins, promote path field, write proofs/tests
from __future__ import annotations
import hashlib, json, re, shutil, struct, textwrap
from pathlib import Path

ROOT = Path(".").resolve()
INV_LIVE = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
INV_STAGE = Path(r"C:\Users\Lenovo\agent-tools\态势信息读取能力清单.md")

# ---- freeze t187-t190 live-SHA pins (t186 pattern) ----
def patch(path: Path, old: str, new: str, label: str):
    t = path.read_text(encoding="utf-8")
    if old not in t:
        raise SystemExit(f"{label}: block not found in {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8")

# t187
patch(
    ROOT / "research/test_t187_input_pause.py",
    '''    def test_inventory_promotes_meta_speed(self):
        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, T187_SHA)
        rec = json.loads((ROOT / "research/t187_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["sha256"], T187_SHA)
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
''',
    '''    def test_inventory_promotes_meta_speed(self):
        rec = json.loads((ROOT / "research/t187_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["sha256"], T187_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t187's recorded hash
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
''',
    "t187",
)

# t188
patch(
    ROOT / "research/test_t188_input_plans.py",
    '''    def test_inventory_unchanged_plans_unverified(self):
        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, T187_SHA)
        rec = json.loads((ROOT / "research/t188_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], T187_SHA)
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
''',
    '''    def test_inventory_unchanged_plans_unverified(self):
        rec = json.loads((ROOT / "research/t188_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], T187_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t188's recorded hash
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
''',
    "t188",
)

# t189
patch(
    ROOT / "research/test_t189_input_crisis_fow_buildings.py",
    '''    def test_inventory_unchanged_no_promotion(self):
        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, LIVE_SHA)
        rec = json.loads((ROOT / "research/t189_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], LIVE_SHA)
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
''',
    '''    def test_inventory_unchanged_no_promotion(self):
        rec = json.loads((ROOT / "research/t189_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], LIVE_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t189's recorded hash
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
''',
    "t189",
)

# t190: freeze SHA and allow later promotions from the t190 unverified set
patch(
    ROOT / "research/test_t190_input_unverified_triage.py",
    '''    def test_triage_covers_all_69_unverified(self):
        inv = INV.read_text(encoding="utf-8")
        unver = [ln.split("|")[1].strip() for ln in inv.splitlines() if "| 未验证 |" in ln]
        self.assertEqual(len(unver), 69)
        tri = json.loads((ROOT / "research/t190_unverified_triage.json").read_text(encoding="utf-8"))
        listed = [r["field"] for r in tri["not_memory"]["fields"]]
        listed += [r["field"] for r in tri["blocked_or_boundary"]["blocked"]]
        listed += [r["field"] for r in tri["blocked_or_boundary"]["boundary"]]
        self.assertEqual(len(listed), 69)
        self.assertEqual(len(set(listed)), 69)
        self.assertEqual(set(listed), set(unver))
        self.assertEqual(tri["not_memory"]["count"], 12)
        self.assertEqual(tri["blocked_or_boundary"]["count"], 57)
        self.assertEqual(tri["independently_pursuable_on_this_snapshot"], [])
        self.assertEqual(tri["promoted"], [])
''',
    '''    def test_triage_covers_all_69_unverified(self):
        inv = INV.read_text(encoding="utf-8")
        unver = [ln.split("|")[1].strip() for ln in inv.splitlines() if "| 未验证 |" in ln]
        tri = json.loads((ROOT / "research/t190_unverified_triage.json").read_text(encoding="utf-8"))
        listed = [r["field"] for r in tri["not_memory"]["fields"]]
        listed += [r["field"] for r in tri["blocked_or_boundary"]["blocked"]]
        listed += [r["field"] for r in tri["blocked_or_boundary"]["boundary"]]
        self.assertEqual(len(listed), 69)
        self.assertEqual(len(set(listed)), 69)
        # later batches may promote a subset of the t190 unverified set
        self.assertTrue(set(unver).issubset(set(listed)))
        self.assertEqual(tri["not_memory"]["count"], 12)
        self.assertEqual(tri["blocked_or_boundary"]["count"], 57)
        self.assertEqual(tri["independently_pursuable_on_this_snapshot"], [])
        self.assertEqual(tri["promoted"], [])
''',
    "t190 triage",
)

patch(
    ROOT / "research/test_t190_input_unverified_triage.py",
    '''    def test_inventory_unchanged(self):
        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, LIVE_SHA)
        rec = json.loads((ROOT / "research/t190_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], LIVE_SHA)
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
''',
    '''    def test_inventory_unchanged(self):
        rec = json.loads((ROOT / "research/t190_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], LIVE_SHA)
        # live D SHA may change in later batches; this test pins t190's recorded hash
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
''',
    "t190 inventory",
)

# ---- input_loaded_fields reader ----
p = ROOT / "calling/input_loaded_fields.py"
t = p.read_text(encoding="utf-8")
needle = "def province_land_neighbors(r, province):\n"
if "def unit_movement_path(" in t:
    print("unit_movement_path already present")
else:
    insert = '''def unit_movement_path(r, army):
    """Official CArmy+0x200 u32 path; empty is not idle. Promoted t191 after a live Move."""
    r.require(army, 'CArmy')
    data, cap, n = struct.unpack('<QII', r.exact(army + 0x200, 16))
    if not 0 <= n <= cap <= 64:
        raise ObservationError('invalid movement path array')
    if n and data < 0x10000:
        raise ObservationError('invalid movement path data')
    if n == 0:
        return []
    raw = r.exact(data, n * 4)
    vals = list(struct.unpack('<' + 'I' * n, raw))
    if not all(1 <= v <= 65535 for v in vals):
        raise ObservationError('invalid path province id')
    return vals


'''
    if needle not in t:
        raise SystemExit("insert point for unit_movement_path not found")
    p.write_text(t.replace(needle, insert + needle, 1), encoding="utf-8")

# ---- offsets.py comment ----
p = ROOT / "calling/offsets.py"
t = p.read_text(encoding="utf-8")
old = '    "CA_PATH": 0x200,  # CPdxArray<u32> movement path; empty (null or size 0) at this idle snapshot'
new = '    "CA_PATH": 0x200,  # CPdxArray<u32> movement path; t191 live Move 1829 5010->8036 read back [8036]. Empty is not idle.'
if old not in t:
    raise SystemExit("CA_PATH comment not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")

# ---- offsets json key ----
offp = ROOT / "calling/tables/offsets_input_windows_1.19.5.json"
off = json.loads(offp.read_text(encoding="utf-8-sig"))
off["move_path_t191"] = {
    "CArmy_path": "+0x200 data / +0x20c size (CPdxArray<u32>)",
    "CArmy_full_path": "+0x220 data / +0x22c size; still empty after this adjacent Move; not promoted as path or target",
    "CArmy_commandlist": "+0x2c0 data / +0x2cc size; still empty; +8 OrderType still unmapped",
    "CArmy_movement_progress": "+0x240; still 0 while paused after Post; eta not promoted",
    "live": {
        "unit_id": 1829,
        "from": 5010,
        "to": 8036,
        "path_after": [8036],
        "province_after": 5010,
        "paused": True,
    },
    "post": {
        "factory_idx": 1402,
        "factory_rva_1_19_5": "0x13fb070",
        "FN_CMD_QUEUE_POST_1_19_5": "0x22c4250",
        "province_buf_kind": "ucrt_malloc",
        "result": "PATH_CONTAINS_DEST",
    },
    "promoted": ["world.own_units.order.path_province_ids"],
    "not_promoted": [
        "world.own_units.order.type",
        "world.own_units.order.target_province_ids",
        "world.own_units.order.eta",
    ],
    "proofs": [
        "research/t191_move_post.json",
        "research/t191_live_path.json",
        "research/t191_factory_slots.json",
        "research/t191_post_rva.json",
    ],
}
offp.write_text(json.dumps(off, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ---- proof json ----
post = json.loads((ROOT / "research/t191_move_post.json").read_text(encoding="utf-8"))
live = json.loads((ROOT / "research/t191_live_path.json").read_text(encoding="utf-8"))
proof = {
    "promoted": ["world.own_units.order.path_province_ids"],
    "not_promoted": {
        "world.own_units.order.type": "commandlist still size 0 after PATH_CONTAINS_DEST; do not invent type=move from a nonempty path",
        "world.own_units.order.target_province_ids": "CArmy+0x220 full_path still empty; do not infer target as path[-1]",
        "world.own_units.order.eta": "CArmy+0x240 movement_progress still 0 while paused; unit has not started moving",
    },
    "ca": "CArmy+0x200 data, +0x20c size; official CPdxArray<u32>",
    "live": {
        "unit_id": 1829,
        "province_id": 5010,
        "path": [8036],
        "other_units_empty_paths": 20,
        "commandlist_size": 0,
        "full_path": [],
        "movement_progress": 0,
        "still_paused": True,
        "speed_index": 0,
        "hour_tick": 60759371,
    },
    "post": {
        "authorized_by": ["pt180u"],
        "factory_idx": 1402,
        "factory_rva": "0x13fb070",
        "FN_CMD_QUEUE_POST": "0x22c4250",
        "result": post.get("result"),
        "province_buf_kind": (post.get("post") or {}).get("province_buf_kind"),
        "path_after": (post.get("post") or {}).get("path_after"),
    },
    "rebase_1_19_5": {
        "ARMY_VT": "0x29d6d98",
        "MOVE_VT": "0x2a2cde0",
        "ACTION_VT": "0x2a1fac8",
        "FACTORY_RVA": "0x13fb070",
        "ACTION_ISVALID_RVA": "0x12c2d10",
        "FN_CMD_QUEUE_POST": "0x22c4250",
        "note": "1.19.4 constants in move_order/post_abi missed the ~+0x70 .text slide and rdata vtable move; rebound from live TYPEID_FACTORY_TABLE + RTTI + pdata before the one-shot Post",
    },
}
(ROOT / "research/t191_move_path.json").write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# ---- official inventory ----
text = INV_LIVE.read_text(encoding="utf-8")
repls = {
    "| world.own_units.order.type | 未验证 | 师当前任务类型，空路径不能证明待机。 |":
    "| world.own_units.order.type | 未验证 | 师当前任务类型。空路径不能证明待机；非空路径也还不是 OrderType，commandlist 在邻省行军后仍为空。 |",
    "| world.own_units.order.target_province_ids | 未验证 | 师当前任务的目标省份。 |":
    "| world.own_units.order.target_province_ids | 未验证 | 师当前任务的目标省份。邻省行军后 CArmy+0x220 full_path 仍为空，不把路径末省推断成 target。 |",
    "| world.own_units.order.path_province_ids | 未验证 | 师有序行军路径，尚无非空路径验收。 |":
    "| world.own_units.order.path_province_ids | 已验证 | 师当前行军路径，取自 CArmy+0x200 的有序 u32 省份数组；活体邻省行军后非空。空路径仍不能证明待机。 |",
    "| world.own_units.order.eta | 未验证 | 该师当前命令的预计到达时间或进度。 |":
    "| world.own_units.order.eta | 未验证 | 该师当前命令的预计到达时间或进度。邻省行军后 CArmy+0x240 在暂停下仍为 0，不升格。 |",
}
for a, b in repls.items():
    if a not in text:
        raise SystemExit(f"inventory line not found: {a}")
    text = text.replace(a, b, 1)

lines = text.splitlines()
# counts
n_tables = sum(1 for ln in lines if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
field_lines = [ln for ln in lines if ln.startswith("| ") and not ln.startswith("| 字段名 |") and not ln.startswith("| ---") and ln.count("|") >= 4]
verified = [ln for ln in field_lines if "| 已验证 |" in ln]
unverified = [ln for ln in field_lines if "| 未验证 |" in ln]
print("tables", n_tables, "fields", len(field_lines), "verified", len(verified), "unverified", len(unverified))
if n_tables != 14 or len(field_lines) != 116 or len(verified) != 48 or len(unverified) != 68:
    raise SystemExit("inventory count mismatch")
if any(("附录" in ln) or ("有序" == ln) for ln in lines):
    pass
# write staged then copy
INV_STAGE.parent.mkdir(parents=True, exist_ok=True)
INV_STAGE.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
shutil.copyfile(INV_STAGE, INV_LIVE)
raw = INV_LIVE.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
# confirm live text
live_text = INV_LIVE.read_text(encoding="utf-8")
assert "| world.own_units.order.path_province_ids | 已验证 |" in live_text
assert "| world.own_units.order.type | 未验证 |" in live_text
rec = {
    "updated": True,
    "sha256": sha,
    "fields": 116,
    "tables": 14,
    "columns": 3,
    "verified": 48,
    "unverified": 68,
    "complete_input": False,
    "promoted": ["world.own_units.order.path_province_ids"],
    "not_promoted": [
        "world.own_units.order.type",
        "world.own_units.order.target_province_ids",
        "world.own_units.order.eta",
    ],
    "source": str(INV_LIVE),
}
(ROOT / "research/t191_inventory_sha256.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("SHA256", sha)
print("wrote inventory and froze earlier pins")
