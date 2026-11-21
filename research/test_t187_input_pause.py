import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T187_SHA = "98d83a601f67b73d71a62c559e9a9a29a75e92eb831c7df2be4d42de7ac7e201"


class Tests(unittest.TestCase):
    def test_cpausegame_calls_idler_virtuals(self):
        ex = (ROOT / "research/_t187_clip_Pause_0xe55060.txt").read_text(encoding="utf-8")
        self.assertIn("0xe55079  call qword ptr [rax + 0x2f0]", ex)
        self.assertIn("0xe5508e  movzx edx, byte ptr [rbx + 0x48]", ex)
        self.assertIn("0xe5509a  jmp qword ptr [rax + 0x298]", ex)
        tok = (ROOT / "research/_t187_clip_Pause_0xe56c30.txt").read_text(encoding="utf-8")
        self.assertIn("0xe56c30  mov dword ptr [rdx], 0x29ec", tok)

    def test_official_getter_is_idler_plus_6c1(self):
        g = (ROOT / "research/_t187_clip_idler_query_vt2f0_0xe46300.txt").read_text(encoding="utf-8")
        self.assertIn("0xe46300  movzx eax, byte ptr [rcx + 0x6c1]", g)
        self.assertIn("0xe46307  ret", g)
        s = (ROOT / "research/_t187_clip_idler_setpause_0xe487f0.txt").read_text(encoding="utf-8")
        self.assertIn("0xe48816  movzx r14d, dl", s)
        self.assertIn("0xe48dd2  mov byte ptr [rbx + 0x6c1], 1", s)
        self.assertIn("0xe48dbb  mov byte ptr [rbx + 0x6c1], 0", s)

    def test_live_flag_is_pause_not_speed_slot(self):
        live = json.loads((ROOT / "research/t187_live_pause.json").read_text(encoding="utf-8"))
        self.assertEqual(live["b6c1"], 1)
        self.assertEqual(live["gs_4bc_i32"], 0)
        self.assertEqual(live["gs_4b8_f32"], 0.0)
        ev = json.loads((ROOT / "research/t187_pause_flag.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["promoted"], ["meta.speed"])
        self.assertEqual(ev["live_value"], "pause")
        self.assertIn("GS_plus_0x4B8", ev["official"]["not_game_pause"])
        self.assertIn("GS_plus_0x4BC", ev["official"]["not_game_pause"])

    def test_token_paused_is_national_focus_not_game(self):
        w = (ROOT / "research/_t187_clip_paused_writer_window.txt").read_text(encoding="utf-8")
        self.assertIn("0x2f52ca  mov edx, 0x3fc3  ; TOKEN activate_shine_on_focus", w)
        self.assertIn("0x2f54d6  mov edx, 0x3691  ; TOKEN paused", w)
        ev = json.loads((ROOT / "research/t187_pause_flag.json").read_text(encoding="utf-8"))
        self.assertIn("national-focus", ev["official"]["not_game_pause"]["token_paused_0x3691"])

    def test_unit_controller_pause_is_not_meta_speed(self):
        ev = json.loads((ROOT / "research/t187_pause_flag.json").read_text(encoding="utf-8"))
        self.assertIn("CArmy", ev["official"]["not_game_pause"]["unit_controller_pause_0x35ba"])

    def test_inventory_promotes_meta_speed(self):
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
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| meta.speed | 已验证 |", text)
        self.assertIn("CInGameIdler+0x6c1", text)
        self.assertIn("| world.wars.front_invalidated | 未验证 |", text)
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertEqual(off["pause_flag_t187"]["CInGameIdler_pause_flag"], "+0x6c1")
        self.assertEqual(off["pause_flag_t187"]["promoted"], ["meta.speed"])
        sess = json.loads((ROOT / "research/t187_session_recheck.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["pid"], 26976)
        self.assertTrue(sess["in_game"])


if __name__ == "__main__":
    unittest.main()
