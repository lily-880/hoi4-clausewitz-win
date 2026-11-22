"""Offline lock for the 12 t245 non-memory fields. Not a promotion.

Does not open a process, call WriteProcessMemory, Post, or read a save.
The exact env value "1" is never passed to Backend.write.
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "calling"))
import config  # noqa: E402
from process import windows as win  # noqa: E402

SCHEMA = json.loads((ROOT / "calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
EVIDENCE = json.loads((Path(__file__).parent / "t246_nonmemory_12.json").read_text(encoding="utf-8"))
CAPTURE = (ROOT / "calling/input_capture_live.py").read_text(encoding="utf-8")
CONFIG_SRC = (ROOT / "calling/config.py").read_text(encoding="utf-8")
WINDOWS_SRC = (ROOT / "calling/process/windows.py").read_text(encoding="utf-8")

CASES = (
    None, "", "0", "false", "False", "no", "True", "true", "TRUE", "yes", "Yes", "1 ", " 1", "1",
)


def _declared(value):
    if value is None:
        os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
    else:
        os.environ["CLAUSEWITZ_ALLOW_WRITE"] = value
    return config.allow_write()


def _effective(value):
    """Return the write-gate result without ever calling WriteProcessMemory."""
    if value is None:
        os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
    else:
        os.environ["CLAUSEWITZ_ALLOW_WRITE"] = value
    if os.environ.get("CLAUSEWITZ_ALLOW_WRITE") == "1":
        return "not_called_exact_1"
    try:
        win.Backend.write(object(), 0, b"\x00")
    except PermissionError:
        return "PermissionError"
    return "returned"


class AllowWriteCurrentBehavior(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("CLAUSEWITZ_ALLOW_WRITE")
        self._post = os.environ.get("CLAUSEWITZ_ALLOW_POST")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
        else:
            os.environ["CLAUSEWITZ_ALLOW_WRITE"] = self._saved
        if self._post is None:
            os.environ.pop("CLAUSEWITZ_ALLOW_POST", None)
        else:
            os.environ["CLAUSEWITZ_ALLOW_POST"] = self._post

    def test_declared_report_disagrees_with_effective_write_gate(self):
        live = []
        for value in CASES:
            live.append({
                "env": "<unset>" if value is None else value,
                "allow_write": _declared(value),
                "backend_write": _effective(value),
            })
        self.assertEqual(live, EVIDENCE["allow_write_matrix"])
        self.assertTrue(any(
            row["allow_write"] is True and row["backend_write"] == "PermissionError"
            for row in live
        ))
        exact = [row for row in live if row["env"] == "1"]
        self.assertEqual(exact, [{"env": "1", "allow_write": True, "backend_write": "not_called_exact_1"}])

    def test_unset_is_closed_and_is_not_field_verification(self):
        os.environ.pop("CLAUSEWITZ_ALLOW_WRITE", None)
        self.assertIs(config.allow_write(), False)
        self.assertEqual(_effective(None), "PermissionError")
        self.assertFalse(EVIDENCE["inventory_promotion"])
        allow = [row for row in EVIDENCE["fields"] if row["field"] == "meta.allow_write"][0]
        self.assertEqual(allow["status"], "behavior_locked_not_promoted")

    def test_write_checks_exact_1_before_memory_call_and_kernel_stays_unbound(self):
        write_src = WINDOWS_SRC.split("def write(", 1)[1].split("def regions(", 1)[0]
        self.assertIn('os.environ.get("CLAUSEWITZ_ALLOW_WRITE") != "1"', write_src)
        self.assertLess(write_src.index("PermissionError"), write_src.index("WriteProcessMemory"))
        self.assertIn('os.environ.get("CLAUSEWITZ_ALLOW_WRITE") == "1"', WINDOWS_SRC)
        self.assertIn("in ('1', 'true', 'TRUE', 'yes')", CONFIG_SRC)
        self.assertNotIn("allow_write()", write_src)
        self.assertIsNone(win.kernel32)
        self.assertFalse(EVIDENCE["allow_write_fix"]["applied"])


class NonMemoryContract(unittest.TestCase):
    def test_twelve_fields_and_no_promotion_counts(self):
        self.assertEqual(EVIDENCE["inventory"]["tables"], 14)
        self.assertEqual(EVIDENCE["inventory"]["fields"], 116)
        self.assertEqual(EVIDENCE["inventory"]["columns"], 3)
        self.assertEqual(EVIDENCE["inventory"]["verified_unverified"], [87, 29])
        self.assertEqual(EVIDENCE["inventory"]["production_type"], 51)
        self.assertIs(EVIDENCE["inventory"]["complete_input"], False)
        self.assertEqual(len(EVIDENCE["fields"]), 12)
        by_name = {row["field"]: row for row in EVIDENCE["fields"]}
        self.assertEqual(len(by_name), 12)
        promoted = [row["field"] for row in EVIDENCE["fields"] if row["status"] == "promoted"]
        self.assertEqual(promoted, [])
        blocked = [row["field"] for row in EVIDENCE["fields"] if row["status"] == "blocked"]
        self.assertEqual(len(blocked), 11)
        self.assertNotIn("meta.allow_write", blocked)
        self.assertEqual(by_name["meta.allow_write"]["status"], "behavior_locked_not_promoted")

    def test_schema_requirements_match_evidence(self):
        meta = SCHEMA["properties"]["meta"]
        policy = SCHEMA["properties"]["policy"]
        feedback = SCHEMA["$defs"]["Feedback"]
        item = feedback["properties"]["last_orders"]["items"]
        self.assertEqual(SCHEMA["required"], ["meta", "policy", "world", "feedback"])
        self.assertEqual(meta["required"], ["game_time", "player_country", "speed", "allow_write", "geography_scope"])
        self.assertEqual(meta["properties"]["allow_write"], {"type": "boolean"})
        self.assertEqual(policy["required"], [])
        self.assertEqual(
            policy["properties"]["stance"]["enum"],
            ["preserve_force", "hold_line", "annihilate", "economize_manpower", "custom"],
        )
        self.assertEqual(policy["properties"]["instructions"], {"type": "string"})
        self.assertEqual(item["required"], ["order_seq", "type", "subject_ids", "accepted"])
        self.assertNotIn("plan_id", item["required"])
        self.assertEqual(item["properties"]["plan_id"], {"type": "integer"})
        self.assertNotIn("error", item["required"])
        self.assertNotIn("ticks_since_issue", feedback["required"])
        self.assertEqual(feedback["properties"]["ticks_since_issue"], {"type": "integer"})
        self.assertIn("Shape validity is not semantic proof", SCHEMA["$comment"])
        scope = meta["properties"]["geography_scope"]["anyOf"]
        self.assertEqual(scope[0], {"type": "null"})
        self.assertEqual(scope[1]["properties"]["kind"]["enum"], ["global"])
        self.assertEqual(scope[2]["properties"]["kind"]["enum"], ["theater"])
        self.assertEqual(EVIDENCE["schema_root_required"], SCHEMA["required"])

    def test_production_capture_does_not_emit_these_fields(self):
        observation = CAPTURE.split("observation={'meta':", 1)[1].split("blocking_checks", 1)[0]
        for key in (
            "allow_write", "geography_scope", "stance", "instructions",
            "last_orders", "ticks_since_issue", "order_seq",
        ):
            self.assertNotIn(key, observation)
        self.assertIn(
            "policy/config allow_write/geography_scope not supplied by memory",
            CAPTURE,
        )
        self.assertIn("feedback ledger", CAPTURE)
        self.assertNotIn("def geography_scope", CONFIG_SRC)
        self.assertNotIn("def stance", CONFIG_SRC)
        self.assertNotIn("last_orders", (ROOT / "calling/command_receipt.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
