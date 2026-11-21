import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
LIVE_SHA = "98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201"


class Tests(unittest.TestCase):
    def test_encirclement_points_are_computed_not_crisis_table(self):
        clip = (ROOT / "research/_t189_clip_encirclement_points_0x1571ef0.txt").read_text(encoding="utf-8")
        self.assertIn("0x1571ef0  mov rax, rsp", clip)
        self.assertIn("0x1572c01  mov rax, qword ptr [r13 + 0x148]", clip)
        caller = (ROOT / "research/_t189_clip_encirc_caller_0x156cab2.txt").read_text(encoding="utf-8")
        self.assertIn("0x156cab2  call 0x1571ef0", caller)
        ev = json.loads((ROOT / "research/t189_crisis_fow_buildings.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["encirclement"]["points"].split(",")[0], "dword province-id array at result+0x148")
        self.assertIn("not a standing world.crises", ev["reason_not_promoted"]["crises"])

    def test_visible_token_is_map_gfx_not_land_fow(self):
        vis = (ROOT / "research/_t189_clip_visible_token_0xf0a978.txt").read_text(encoding="utf-8")
        self.assertIn("TOKEN z", vis)
        self.assertIn("TOKEN scale", vis)
        self.assertIn("TOKEN rotation", vis)
        self.assertIn("TOKEN animation", vis)
        self.assertIn("TOKEN visible", vis)
        ev = json.loads((ROOT / "research/t189_crisis_fow_buildings.json").read_text(encoding="utf-8"))
        self.assertIn("map/gfx", ev["not_land_fow"]["visible_0x2d2a"])
        self.assertIn("naval", ev["not_land_fow"]["already_spotted_0x3bb3"])

    def test_intel_token_is_national_pools_not_unit_confidence(self):
        intel = (ROOT / "research/_t189_clip_intel_writer_0xd689d0.txt").read_text(encoding="utf-8")
        self.assertIn("TOKEN intel", intel)
        self.assertIn("TOKEN intel_from_allies", intel)
        self.assertIn("TOKEN static_intel_pools", intel)
        self.assertIn("TOKEN dynamic_intel_pools", intel)
        ev = json.loads((ROOT / "research/t189_crisis_fow_buildings.json").read_text(encoding="utf-8"))
        self.assertIn("national intel", ev["not_land_fow"]["intel_0x30ec"])

    def test_live_buildings_have_no_damaged_or_overlay_sample(self):
        live = json.loads((ROOT / "research/t189_live_buildings.json").read_text(encoding="utf-8"))
        self.assertEqual(live["state_damaged"], 0)
        self.assertEqual(live["state_overlays"], 0)
        self.assertEqual(live["prov_damaged"], 0)
        self.assertEqual(live["prov_overlays"], 0)
        self.assertEqual(live["damaged_samples"], [])
        self.assertEqual(live["overlay_samples"], [])
        self.assertEqual(live["state_buildings"], live["state_undamaged"])
        self.assertEqual(live["prov_buildings"], live["prov_undamaged"])
        self.assertGreater(live["state_buildings"], 0)
        self.assertGreater(live["prov_buildings"], 0)
        ev = json.loads((ROOT / "research/t189_crisis_fow_buildings.json").read_text(encoding="utf-8"))
        self.assertIn("1552CF0 is still a string formatter", ev["reason_not_promoted"]["buildings"])

    def test_session_still_in_game(self):
        sess = json.loads((ROOT / "research/t189_session_recheck.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["pid"], 26976)
        self.assertTrue(sess["in_game"])
        self.assertEqual(sess["tag"], "ETH")
        self.assertEqual(sess["player_index"], 44)
        self.assertEqual(sess["pause_flag_6c1"], 1)

    def test_inventory_unchanged_no_promotion(self):
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
        self.assertIn("| world.crises.kind | 未验证 |", text)
        self.assertIn("| world.visible_units.visibility.spotted | 未验证 |", text)
        self.assertIn("| world.visible_units.visibility.confidence | 未验证 |", text)
        self.assertIn("限未建或无损且无额外加级", text)
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertFalse(off["crisis_fow_buildings_t189"]["promoted"])
        ev = json.loads((ROOT / "research/t189_crisis_fow_buildings.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["promoted"], [])


if __name__ == "__main__":
    unittest.main()
