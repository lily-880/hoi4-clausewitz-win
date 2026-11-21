import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T191_SHA = "e38f089d93bbbfa7dd081966bc7f43ada13bd960f74513e2c38c55861bc4c9fc"


class Tests(unittest.TestCase):
    def test_factory_rebased_to_1_19_5(self):
        ev = json.loads((ROOT / "research/t191_move_path.json").read_text(encoding="utf-8"))
        rb = ev["rebase_1_19_5"]
        self.assertEqual(rb["FACTORY_RVA"], "0x13fb070")
        self.assertEqual(rb["FN_CMD_QUEUE_POST"], "0x22c4250")
        self.assertEqual(rb["ARMY_VT"], "0x29d6d98")
        self.assertEqual(rb["MOVE_VT"], "0x2a2cde0")
        self.assertEqual(rb["ACTION_VT"], "0x2a1fac8")
        slots = json.loads((ROOT / "research/t191_factory_slots.json").read_text(encoding="utf-8"))
        self.assertEqual(slots["factory_slots"]["MOVE"]["rva"], "0x13fb070")
        self.assertTrue(slots["factory_slots"]["MOVE"]["head16"].endswith("b988000000") or "b988000000" in slots["factory_slots"]["MOVE"]["head16"])
        post_rva = json.loads((ROOT / "research/t191_post_rva.json").read_text(encoding="utf-8"))
        self.assertEqual(post_rva["live_server_rtti"], ".?AVCDummyServer@@")
        self.assertEqual(post_rva["dummy_vt_slots"]["0x2bcbea0"]["slots"][1]["rva"], "0x23f5d40")
        clip = (ROOT / "research/_t191_clip_fn_post_0x22c4250.txt").read_text(encoding="utf-8")
        self.assertIn("0x22c427e  cmp byte ptr [rcx + 0x725], sil", clip)
        self.assertIn("0x22c4710  mov rcx, qword ptr [rbx + 0x40]", clip)
        self.assertIn("0x22c471a  call qword ptr [rax + 0x28]", clip)

    def test_post_path_contains_dest(self):
        post = json.loads((ROOT / "research/t191_move_post.json").read_text(encoding="utf-8"))
        self.assertEqual(post["unit_id"], 1829)
        self.assertEqual(post["src_province"], 5010)
        self.assertEqual(post["dest_province"], 8036)
        self.assertEqual(post["dry_run"]["result"], "DRY_RUN_VALID")
        self.assertEqual(post["result"], "PATH_CONTAINS_DEST")
        self.assertEqual(post["post"]["path_after"], [8036])
        self.assertEqual(post["post"]["province_buf_kind"], "ucrt_malloc")
        self.assertTrue(post["path_contains_dest"])
        self.assertTrue(post["province_unchanged"])
        self.assertTrue(post["still_paused"])
        self.assertEqual(post["speed_index_after"], 0)
        self.assertFalse(post["commandlist_nonempty"])
        self.assertTrue(post["gate_closed"]["allow_post_after_close"] is False)
        self.assertFalse(post["gate_closed"]["marker_exists"])

    def test_live_readback_only_1829_has_path(self):
        live = json.loads((ROOT / "research/t191_live_path.json").read_text(encoding="utf-8"))
        self.assertEqual(live["pid"], 26976)
        self.assertEqual(live["pause_flag_6c1"], 1)
        self.assertEqual(live["speed_index"], 0)
        self.assertEqual(live["n_units"], 21)
        self.assertEqual(len(live["nonempty_paths"]), 1)
        row = live["nonempty_paths"][0]
        self.assertEqual(row["unit_id"], 1829)
        self.assertEqual(row["province_id"], 5010)
        self.assertEqual(row["path"], [8036])
        self.assertEqual(row["full_path"], [])
        self.assertEqual(row["commandlist_size"], 0)
        self.assertEqual(row["movement_progress"], 0)
        self.assertEqual(live["nonempty_full_paths"], [])
        self.assertEqual(live["nonempty_commandlists"], [])

    def test_type_target_eta_not_promoted(self):
        ev = json.loads((ROOT / "research/t191_move_path.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["promoted"], ["world.own_units.order.path_province_ids"])
        self.assertIn("world.own_units.order.type", ev["not_promoted"])
        self.assertIn("world.own_units.order.target_province_ids", ev["not_promoted"])
        self.assertIn("world.own_units.order.eta", ev["not_promoted"])
        self.assertIn("commandlist", ev["not_promoted"]["world.own_units.order.type"])
        self.assertIn("full_path", ev["not_promoted"]["world.own_units.order.target_province_ids"])
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertEqual(off["move_path_t191"]["promoted"], ["world.own_units.order.path_province_ids"])
        self.assertEqual(len(off["move_path_t191"]["not_promoted"]), 3)

    def test_inventory_promotes_path_only(self):
        rec = json.loads((ROOT / "research/t191_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["sha256"], T191_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t191's recorded hash
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["tables"], 14)
        self.assertEqual(rec["columns"], 3)
        self.assertEqual(rec["verified"], 48)
        self.assertEqual(rec["unverified"], 68)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.order.path_province_ids | 已验证 |", text)
        self.assertIn("CArmy+0x200", text)
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
        self.assertIn("| world.own_units.order.target_province_ids | 未验证 |", text)
        self.assertIn("| world.own_units.order.eta | 未验证 |", text)
        self.assertIn("| meta.speed | 已验证 |", text)
        self.assertNotIn("附录", text)
        n_tables = sum(1 for ln in text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
        self.assertEqual(n_tables, 14)

    def test_reader_and_constants_exist(self):
        src = (ROOT / "calling/input_loaded_fields.py").read_text(encoding="utf-8")
        self.assertIn("def unit_movement_path(", src)
        self.assertIn("army + 0x200", src)
        mo = (ROOT / "calling/move_order.py").read_text(encoding="utf-8")
        self.assertIn("FACTORY_RVA = 0x13FB070", mo)
        self.assertIn("ARMY_VT = 0x29D6D98", mo)
        abi = (ROOT / "calling/post_abi.py").read_text(encoding="utf-8")
        self.assertIn("FN_CMD_QUEUE_POST = 0x22C4250", abi)
        sess = json.loads((ROOT / "research/t191_session_recheck.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["pid"], 26976)
        self.assertTrue(sess["in_game"])
        self.assertEqual(sess["pause_flag_6c1"], 1)


if __name__ == "__main__":
    unittest.main()
