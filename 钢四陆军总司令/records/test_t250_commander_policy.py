"""Offline checks for the saved global scope and annihilate stance.

Does not import capture, open a process, or rewrite the pinned producers.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "calling"))
import commander_config as cc  # noqa: E402

PINS = {
    "calling/input_capture_live.py": "e10bf427df1059c3f16873960bcbdabef826ef1dc058ad5e087b5a67d8087d37",
    "calling/input_loaded_fields.py": "1aecf151e7f221fa2f1a6b86b37a9d15bf2a44d0f7f649f552b2af8f808e65b5",
    "calling/tables/generalissimo_input.schema.json": "9a941dd3931b635591582b0d2ba3fe7ab1ceb3554a2d30af54154e61071b45ee",
    "calling/input_observation.py": "27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6",
}


def _write(doc):
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    json.dump(doc, handle)
    handle.close()
    return Path(handle.name)


class SavedChoice(unittest.TestCase):
    def test_user_file_yields_global_and_annihilate(self):
        got = cc.load_commander_policy()
        self.assertEqual(got, {
            "meta": {"geography_scope": {"kind": "global"}},
            "policy": {"stance": "annihilate"},
        })
        text = cc.DEFAULT_PATH.read_text(encoding="utf-8")
        self.assertIn("总司令地理范围选 global，负责全球陆战。", text)
        self.assertIn("默认方针选 annihilate，歼灭敌军。", text)
        self.assertNotIn("instructions", text)
        self.assertNotIn("allow_write", text)

    def test_merge_fills_only_the_two_fields(self):
        base = {"meta": {"game_time": {"year": 1936}}, "world": {}}
        got = cc.merge_commander_policy(base)
        self.assertEqual(got["meta"]["geography_scope"], {"kind": "global"})
        self.assertEqual(got["meta"]["game_time"], {"year": 1936})
        self.assertEqual(got["policy"], {"stance": "annihilate"})
        self.assertNotIn("instructions", got["policy"])
        self.assertNotIn("feedback", got)
        self.assertNotIn("complete_input", got)
        self.assertNotIn("allow_write", got["meta"])
        self.assertNotIn("geography_scope", base["meta"])

    def test_shape_matches_schema_branches(self):
        schema = json.loads(cc.SCHEMA_PATH.read_text(encoding="utf-8"))
        got = cc.load_commander_policy()
        scope = got["meta"]["geography_scope"]
        global_branch = schema["properties"]["meta"]["properties"]["geography_scope"]["anyOf"][1]
        self.assertEqual(set(scope), set(global_branch["required"]))
        self.assertEqual(scope["kind"], global_branch["properties"]["kind"]["enum"][0])
        self.assertIn(got["policy"]["stance"], schema["properties"]["policy"]["properties"]["stance"]["enum"])
        self.assertEqual(schema["properties"]["policy"]["required"], [])

    def test_module_has_no_stance_default_literal(self):
        source = (ROOT / "calling/commander_config.py").read_text(encoding="utf-8")
        self.assertNotIn("annihilate", source)
        self.assertNotIn("CLAUSEWITZ_ALLOW_WRITE", source)
        self.assertNotIn("WriteProcessMemory", source)


class Rejection(unittest.TestCase):
    def test_missing_file_and_empty_object_do_not_invent_values(self):
        with self.assertRaises(cc.CommanderConfigError) as missing:
            cc.load_commander_policy(ROOT / "calling/tables/no_such_commander_policy.json")
        self.assertEqual(missing.exception.code, "missing_file")
        path = _write({})
        with self.assertRaises(cc.CommanderConfigError) as empty:
            cc.load_commander_policy(path)
        self.assertEqual(empty.exception.code, "missing_geography_scope")

    def test_null_scope_is_not_global_and_partial_files_do_not_fill_the_other(self):
        null_scope = _write({"geography_scope": None, "policy": {"stance": "annihilate"}})
        with self.assertRaises(cc.CommanderConfigError) as null_case:
            cc.load_commander_policy(null_scope)
        self.assertEqual(null_case.exception.code, "null_geography_scope")
        scope_only = _write({"geography_scope": {"kind": "global"}})
        with self.assertRaises(cc.CommanderConfigError) as no_stance:
            cc.load_commander_policy(scope_only)
        self.assertEqual(no_stance.exception.code, "missing_stance")
        stance_only = _write({"policy": {"stance": "annihilate"}})
        with self.assertRaises(cc.CommanderConfigError) as no_scope:
            cc.load_commander_policy(stance_only)
        self.assertEqual(no_scope.exception.code, "missing_geography_scope")

    def test_illegal_and_conflicting_values_are_rejected(self):
        cases = [
            ({"geography_scope": {"kind": "sea"}, "policy": {"stance": "annihilate"}}, "illegal_geography_scope"),
            ({"geography_scope": {"kind": "global", "province_ids": [1]}, "policy": {"stance": "annihilate"}}, "conflicting_geography_scope"),
            ({"geography_scope": {"kind": "theater"}, "policy": {"stance": "annihilate"}}, "illegal_geography_scope"),
            ({"geography_scope": {"kind": "theater", "province_ids": [True]}, "policy": {"stance": "annihilate"}}, "illegal_geography_scope"),
            ({"geography_scope": {"kind": "global"}, "policy": {"stance": "blitz"}}, "illegal_stance"),
            ({"geography_scope": {"kind": "global"}, "policy": {"stance": "annihilate", "instructions": "advance"}}, "instructions_not_accepted"),
            ({"geography_scope": {"kind": "global"}, "policy": {"stance": "annihilate"}, "allow_write": True}, "illegal_file"),
        ]
        for doc, code in cases:
            with self.assertRaises(cc.CommanderConfigError) as caught:
                cc.load_commander_policy(_write(doc))
            self.assertEqual(caught.exception.code, code)

    def test_explicit_other_values_stay_unchanged(self):
        path = _write({
            "geography_scope": {"kind": "theater", "province_ids": [10, 11]},
            "policy": {"stance": "hold_line"},
        })
        got = cc.load_commander_policy(path)
        self.assertEqual(got["meta"]["geography_scope"], {"kind": "theater", "province_ids": [10, 11]})
        self.assertEqual(got["policy"]["stance"], "hold_line")

    def test_merge_does_not_overwrite_conflict_or_existing_instructions(self):
        with self.assertRaises(cc.CommanderConfigError) as scope_conflict:
            cc.merge_commander_policy({"meta": {"geography_scope": None}})
        self.assertEqual(scope_conflict.exception.code, "conflicting_geography_scope")
        with self.assertRaises(cc.CommanderConfigError) as stance_conflict:
            cc.merge_commander_policy({"policy": {"stance": "hold_line"}})
        self.assertEqual(stance_conflict.exception.code, "conflicting_stance")
        kept = cc.merge_commander_policy({"policy": {"instructions": "hold the river"}})
        self.assertEqual(kept["policy"]["instructions"], "hold the river")
        self.assertEqual(kept["policy"]["stance"], "annihilate")
        self.assertEqual(kept["meta"]["geography_scope"], {"kind": "global"})


class Boundaries(unittest.TestCase):
    def test_pins_write_gate_and_capture_hook_stay_untouched(self):
        for rel, digest in PINS.items():
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), digest)
        config_src = (ROOT / "calling/config.py").read_text(encoding="utf-8")
        windows_src = (ROOT / "calling/process/windows.py").read_text(encoding="utf-8")
        self.assertIn("in ('1', 'true', 'TRUE', 'yes')", config_src)
        self.assertIn('os.environ.get("CLAUSEWITZ_ALLOW_WRITE") != "1"', windows_src)
        capture = (ROOT / "calling/input_capture_live.py").read_text(encoding="utf-8")
        self.assertNotIn("commander_config", capture)
        self.assertNotIn("commander_policy", capture)
        self.assertIn("policy/config allow_write/geography_scope not supplied by memory", capture)


if __name__ == "__main__":
    unittest.main(verbosity=2)
