"""Offline counterexample for the t240 owner-join equality.

Uses the committed t253 unit 1101 facts. Does not read a process,
rename offsets, or emit a relation.
"""
import ast
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OBSERVATION = ROOT / "calling/input_observation.py"
PIN = "27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6"
COLLECTOR = ROOT / "research/t240_current_owner_directional_operands.py"


def _observation_owner_gate():
    tree = ast.parse(OBSERVATION.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "observe_own_divisions":
            return ast.get_source_segment(OBSERVATION.read_text(encoding="utf-8"), node)
    raise AssertionError("observe_own_divisions missing")


class Counterexample(unittest.TestCase):
    def test_unit_1101_falsifies_universal_remap_equality(self):
        raw_1d8, remap_1d8, tag_1d8 = 16, 16, "ITA"
        raw_1e0, remap_1e0, tag_1e0 = 3, 3, "SOV"
        self.assertNotEqual((remap_1d8, tag_1d8), (remap_1e0, tag_1e0))
        self.assertNotEqual(remap_1d8, raw_1e0)
        self.assertEqual(raw_1d8, remap_1d8)
        self.assertEqual(raw_1e0, remap_1e0)
        self.assertEqual(51, 0x33)

    def test_equality_assert_is_research_collector_not_production(self):
        collector = COLLECTOR.read_text(encoding="utf-8")
        self.assertIn("raw_owner=r.i(up+0x1d8)", collector)
        self.assertIn("stored_index=r.i(up+0x1e0)", collector)
        self.assertIn("assert owner_index==stored_index", collector)
        production = _observation_owner_gate()
        self.assertNotIn("0x1d8", production)
        self.assertNotIn("remap", production)
        self.assertIn("owner = unpack('<i', blob, 0x1e0)", production)
        self.assertIn("owner != player_index", production)
        self.assertIn("'relation_to_player': 'self'", production)

    def test_counterexample_emits_no_relation_and_pin_stays(self):
        self.assertEqual(hashlib.sha256(OBSERVATION.read_bytes()).hexdigest(), PIN)
        relation = None
        self.assertIsNone(relation)


if __name__ == "__main__":
    unittest.main(verbosity=2)
