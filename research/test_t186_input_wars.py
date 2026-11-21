import json, hashlib, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
T186_SHA = "2bf707a0a097487bb6e17797ab6cde12e6dcaf9203c90a3f984c222474299d62"


class Tests(unittest.TestCase):
    def test_warrelation_writer_first_second_and_state_gates(self):
        base = (ROOT / "research/_t186_clip_relation_base_0xd8f520.txt").read_text(encoding="utf-8")
        self.assertIn("0xd8f530  add rcx, 0x10", base)
        self.assertIn("0xd8f53f  mov edx, 0x28de  ; TOKEN first", base)
        self.assertIn("0xd8f54c  lea rcx, [rbx + 0x14]", base)
        self.assertIn("0xd8f55b  mov edx, 0x28df  ; TOKEN second", base)
        self.assertIn("0xd8f568  cmp byte ptr [rbx + 0x48], 0", base)
        self.assertIn("0xd8f574  mov edx, 0x28e5  ; TOKEN cancel", base)
        self.assertIn("0xd8f584  mov edx, 0x28e0  ; TOKEN start_date", base)
        self.assertIn("0xd8f591  cmp dword ptr [rbx + 0x38], eax", base)
        self.assertIn("0xd8f59a  mov edx, 0x28e1  ; TOKEN end_date", base)
        wr = (ROOT / "research/_t186_clip_warrelation_writer_0xd8f900.txt").read_text(encoding="utf-8")
        self.assertIn("0xd8f91c  call 0xd8f520", wr)
        self.assertIn("0xd8f9a6  mov edx, 0x3af7  ; TOKEN first_was_instigator", wr)
        self.assertIn("0xd8fb13  mov r8d, 0x298d  ; TOKEN war", wr)
        self.assertIn("0xd8fb41  mov edx, 0x381d  ; TOKEN hostility_reason_instigator", wr)

    def test_official_plus_2e8_getter(self):
        g = (ROOT / "research/_t186_clip_getter_0xd7db8b.txt").read_text(encoding="utf-8")
        self.assertIn("0xd7db99  mov rsi, qword ptr [rax + 0xf88]", g)
        self.assertIn("0xd7dbbf  mov rax, qword ptr [rcx + 0x2e8]", g)
        use = (ROOT / "research/_t186_clip_use_0xd82c10.txt").read_text(encoding="utf-8")
        self.assertIn("0xd82c10  mov rcx, qword ptr [rcx + 0x2e8]", use)
        self.assertIn("0xd82c20  cmp byte ptr [rcx + 0x49], 0", use)
        ev = json.loads((ROOT / "research/t186_war_writers.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["CRelationStatus"]["war_relation_slot"], "+0x2e8 CWarRelation*")
        self.assertIn("0xd7db8b", ev["CRelationStatus"]["official_getters"])

    def test_live_eth_ita_is_only_world_war(self):
        world = json.loads((ROOT / "research/t186_world_warrelations.json").read_text(encoding="utf-8"))
        self.assertEqual(world["n"], 1)
        w = world["wars"][0]
        self.assertEqual(w["first"], 16)
        self.assertEqual(w["first_tag"], "ITA")
        self.assertEqual(w["second"], 44)
        self.assertEqual(w["second_tag"], "ETH")
        self.assertEqual(w["cancel"], 0)
        live = json.loads((ROOT / "research/t186_live_warrelation.json").read_text(encoding="utf-8"))
        dumps = live["war_dumps"]
        self.assertGreaterEqual(len(dumps), 2)
        self.assertTrue(all(d["ptr"] == "0x26c70b635d0" for d in dumps))
        self.assertTrue(all(d["cancel_48"] == 0 for d in dumps))
        self.assertTrue(all(d["first_was_instigator_158"] == 1 for d in dumps))
        ev = json.loads((ROOT / "research/t186_war_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["live"]["state"], "at_war")
        self.assertTrue(ev["do_not_map_hostility_reason_to_state"])

    def test_active_relations_are_not_wars(self):
        hist = json.loads((ROOT / "research/t186_live_eth_relations.json").read_text(encoding="utf-8"))
        self.assertEqual(hist["size"], 440)
        self.assertEqual(hist["class_hist"].get(".?AVCRelationStatus@@"), 440)
        self.assertEqual(len(hist["wars"]), 0)
        ev = json.loads((ROOT / "research/t186_war_writers.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["CDiplomacyStatus"]["active_relations"].split(",")[0], "token 0x2e43")

    def test_front_invalidated_not_promoted(self):
        ev = json.loads((ROOT / "research/t186_war_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(ev["mapping"]["front_invalidated"], "no named token; not promoted")
        off = json.loads((ROOT / "calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8"))
        self.assertFalse(off["war_relation_t186"]["promoted_front_invalidated"])
        self.assertEqual(off["war_relation_t186"]["promoted"], ["world.wars.a", "world.wars.b", "world.wars.state"])

    def test_inventory_promotes_wars_ab_state(self):
        rec = json.loads((ROOT / "research/t186_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["sha256"], T186_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t186's recorded hash
        self.assertEqual(rec["fields"], 116)
        self.assertEqual(rec["verified"], 46)
        self.assertEqual(rec["unverified"], 70)
        self.assertFalse(rec["complete_input"])
        text = raw.decode("utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.wars.a | 已验证 |", text)
        self.assertIn("| world.wars.b | 已验证 |", text)
        self.assertIn("| world.wars.state | 已验证 |", text)
        self.assertIn("| world.wars.front_invalidated | 未验证 |", text)
        self.assertIn("ITA", text)
        self.assertIn("ETH", text)
        self.assertIn("at_war", text)
        sess = json.loads((ROOT / "research/t186_session_recheck.json").read_text(encoding="utf-8"))
        self.assertEqual(sess["pid"], 26976)
        self.assertTrue(sess["in_game"])


if __name__ == "__main__":
    unittest.main()
