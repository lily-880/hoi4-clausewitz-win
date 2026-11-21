import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
LIVE_SHA = "98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201"


class Tests(unittest.TestCase):
    def test_triage_covers_all_69_unverified(self):
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

    def test_config_and_feedback_are_not_memory(self):
        tri = json.loads((ROOT / "research/t190_unverified_triage.json").read_text(encoding="utf-8"))
        by = {r["field"]: r for r in tri["not_memory"]["fields"]}
        self.assertEqual(by["meta.allow_write"]["bucket"], "config")
        self.assertEqual(by["policy.instructions"]["bucket"], "config")
        self.assertEqual(by["feedback.last_orders.order_seq"]["bucket"], "ledger")
        self.assertEqual(by["feedback.ticks_since_issue"]["bucket"], "ledger")

    def test_cc6480_gap_is_zero_and_not_promoted(self):
        clip = (ROOT / "research/_t190_clip_cc6480.txt").read_text(encoding="utf-8")
        self.assertIn("0xcc648d  add rcx, 8", clip)
        self.assertIn("0xcc6491  call 0xcc6570", clip)
        self.assertIn("0xcc6496  lea rcx, [rdi + 0x28]", clip)
        self.assertIn("0xcc64af  cmovns eax, ecx", clip)
        live = json.loads((ROOT / "research/t190_live_manpower_gap.json").read_text(encoding="utf-8"))
        self.assertEqual(live["n_units"], 21)
        self.assertTrue(live["backlink_ok"])
        self.assertEqual(live["current_total"], 105000)
        self.assertEqual(live["need_total"], 105000)
        self.assertEqual(live["gap_total"], 0)
        self.assertEqual(live["units_with_gap"], [])
        tri = json.loads((ROOT / "research/t190_unverified_triage.json").read_text(encoding="utf-8"))
        needed = [r for r in tri["blocked_or_boundary"]["boundary"] if r["field"]=="world.shortages.manpower.needed"][0]
        self.assertIn("不把满员 0 升格", needed["reason"])

    def test_session_still_in_game(self):
        sess = json.loads((ROOT / "research/t190_session_recheck.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["pid"], 26976)
        self.assertTrue(sess["in_game"])
        self.assertEqual(sess["tag"], "ETH")
        self.assertEqual(sess["pause_flag_6c1"], 1)

    def test_inventory_unchanged(self):
        rec = json.loads((ROOT / "research/t190_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertFalse(rec["updated"])
        self.assertEqual(rec["sha256"], LIVE_SHA)
        # live D SHA may change in later batches; this test pins t190's recorded hash
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 47)
        self.assertEqual(rec["unverified"], 69)
        self.assertFalse(rec["complete_input"])
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertFalse(off["unverified_triage_t190"]["promoted"])
        self.assertEqual(off["unverified_triage_t190"]["independently_pursuable_on_this_snapshot"], [])

    def test_triage_does_not_split_or_mark_config_verified(self):
        rec = json.loads((ROOT / "research/t190_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["promoted"], [])
        text = INV.read_text(encoding="utf-8")
        self.assertIn("| meta.allow_write | 未验证 |", text)
        self.assertIn("| feedback.last_orders.order_seq | 未验证 |", text)
        self.assertIn("| world.shortages.manpower.needed | 未验证 |", text)


if __name__ == "__main__":
    unittest.main()
