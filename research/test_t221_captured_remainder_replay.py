import ast, json, unittest
from pathlib import Path
import t221_captured_remainder_replay as m
Q = Path(__file__).parent
class RemainderReplayTests(unittest.TestCase):
    def setUp(self):
        self.ui = json.loads((Q/"t221_logistics_ui_balance_consumers.json").read_text())
        self.generic = json.loads((Q/"t221_generic_slot_readers_and_literals.json").read_text())
        self.fmt = json.loads((Q/"t221_remainder_formatter_and_1409700.json").read_text())
        self.cur = json.loads((Q/"t221_1409700_closed_and_current_remainders.json").read_text())
        self.train = json.loads((Q/"t220_train_motor_independent_positive_samples.json").read_text())
    def runproof(self):
        return m.replay(self.ui, self.generic, self.fmt, self.cur, self.train)
    def reject(self):
        with self.assertRaises((ValueError, KeyError, TypeError)):
            self.runproof()
    def test_01_train_remainder_is_uncommitted_68_not_total_83(self):
        r = self.runproof()["train_equipment"]
        self.assertEqual((r["signed_remainder_raw"], r["cache15_raw"], r["nonnegative_shortfall"]), (6800000, 8300000, 0))
    def test_02_train_commitment_15_is_not_deficit(self):
        self.assertEqual((m.TRAIN_TOTAL - m.TRAIN_COMMITMENT) * m.FIXED, 6800000)
        self.assertNotEqual(m.TRAIN_COMMITMENT, self.runproof()["train_equipment"]["nonnegative_shortfall"])
    def test_03_infantry_shortfall_equals_demanded_10015(self):
        self.assertEqual(self.runproof()["infantry_equipment"]["nonnegative_shortfall"], 10015)
    def test_04_artillery_shortfall_147(self):
        self.assertEqual(self.runproof()["artillery_equipment"]["nonnegative_shortfall"], 147)
    def test_05_support_shortfall_121(self):
        self.assertEqual(self.runproof()["support_equipment"]["nonnegative_shortfall"], 121)
    def test_06_light_tank_shortfall_2324(self):
        self.assertEqual(self.runproof()["light_tank_chassis"]["nonnegative_shortfall"], 2324)
    def test_07_motorized_shortfall_1278(self):
        self.assertEqual(self.runproof()["motorized_equipment"]["nonnegative_shortfall"], 1278)
    def test_08_official_balance_token_is_not_equipment_remainder(self):
        self.runproof()
        text = "\n".join(x for x in self.ui["flows"]["0x1e1f6a0"]["asm"] if "1e20158" <= x.split()[0] <= "1e20260")
        self.assertIn("0x608", text)
        self.assertNotIn("0x5f8", text)
    def test_09_official_need_is_hidden_subtrahend_not_needs_token(self):
        text = "\n".join(self.ui["flows"]["0x1e1f6a0"]["asm"])
        self.assertEqual(text.count("0x648"), 1)
        self.runproof()
    def test_10_no_deficit_named_token(self):
        text = "\n".join(self.ui["flows"]["0x1e1f6a0"]["asm"] + self.ui["flows"]["0x1e208f0"]["asm"]).lower()
        self.assertNotIn("deficit", text)
        self.runproof()
    def test_11_negative_slot15_is_clamped_in_current_not_added_to_remainder(self):
        r = self.runproof()["infantry_equipment"]
        self.assertEqual(r["cache15_raw"], -75000)
        self.assertEqual(r["signed_remainder_raw"], -1001500000)
    def test_12_1409700_empty_so_aggregate_addend_is_zero(self):
        self.assertEqual(self.cur["countryresources"]["count77c"], 0)
        self.runproof()
    def test_13_rejects_using_train_total_as_remainder(self):
        self.cur["six_type_slot_values"]["train_equipment"]["cache16"] = 8300000
        self.reject()
    def test_14_rejects_using_commitment_as_train_deficit(self):
        self.cur["six_type_slot_values"]["train_equipment"]["cache16"] = -1500000
        self.reject()
    def test_15_rejects_stale_train_cache(self):
        self.train["types"]["train_equipment"]["cache16_raw"] += 1
        self.reject()
    def test_16_rejects_changed_train_total_counter(self):
        self.train["counters"]["train_total_plus110"] = 82
        self.reject()
    def test_17_rejects_nonempty_1409700_array(self):
        self.cur["countryresources"]["count77c"] = 1
        self.reject()
    def test_18_rejects_missing_in_stock_subtract(self):
        asm = self.ui["flows"]["0x1e1f6a0"]["asm"]
        self.ui["flows"]["0x1e1f6a0"]["asm"] = [x.replace("sub qword ptr [r15 + 0x5f8], r8", "nop") for x in asm]
        self.reject()
    def test_19_rejects_rebinding_balance_to_remainder_field(self):
        asm = self.ui["flows"]["0x1e1f6a0"]["asm"]
        self.ui["flows"]["0x1e1f6a0"]["asm"] = [x.replace("[r15 + 0x608]", "[r15 + 0x5f8]") if x.startswith("1e20186") or x.startswith("1e201f2") else x for x in asm]
        self.reject()
    def test_20_rejects_native_formatter_byte_change(self):
        self.fmt["flows"]["0x1e1a680"]["raw_hex"] = "00" + self.fmt["flows"]["0x1e1a680"]["raw_hex"][2:]
        self.reject()
    def test_21_rejects_unclosed_ui_consumer(self):
        self.ui["flows"]["0x1e1f6a0"]["unresolved_edges"] = [{"reason": "synthetic"}]
        self.reject()
    def test_22_rejects_changed_tick(self):
        self.cur["after"]["hour_tick"] += 1
        self.reject()
    def test_23_rejects_open_gate(self):
        self.cur["before"]["markers"]["safe_land_tool_gate.OPEN"] = True
        self.reject()
    def test_24_rejects_boolean_remainder(self):
        self.cur["six_type_slot_values"]["infantry_equipment"]["cache16"] = True
        self.reject()
    def test_25_rejects_fractional_shortfall(self):
        self.cur["six_type_slot_values"]["artillery_equipment"]["cache16"] = -14700001
        self.reject()
    def test_26_rejects_wrong_pid(self):
        self.cur["before"]["pid"] = 6496
        self.reject()
    def test_27_replay_has_no_process_import(self):
        tree = ast.parse((Q/"t221_captured_remainder_replay.py").read_text())
        names = {n.name for x in ast.walk(tree) if isinstance(x, ast.Import) for n in x.names}
        self.assertEqual(names, {"hashlib"})
    def test_28_all_six_scopes_and_no_deficit_promotion_helper(self):
        r = self.runproof()
        self.assertEqual(set(r), set(m.SCOPE))
        self.assertFalse(hasattr(m, "promote_deficit"))
if __name__ == "__main__":
    unittest.main()
