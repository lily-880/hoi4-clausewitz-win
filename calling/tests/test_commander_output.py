#!/usr/bin/env python3
"""Offline tests for the GeneralissimoOutput contract and decide_v0.

No live backend is imported; no process, Post, or save access.
Run: python -I calling/tests/test_commander_output.py -v
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CALLING = ROOT / "calling"
sys.path.insert(0, str(CALLING))

import decide_v0  # noqa: E402
import generalissimo_output as g  # noqa: E402

BACKEND_MODULES = ("mem", "pe", "gamestate", "handle", "process", "config", "post_abi")
FIXTURES = (ROOT / "research" / "t201_full_capture_recursive_a.json",
            ROOT / "research" / "t201_full_capture_recursive_b.json")
INPUT_SCHEMA = CALLING / "tables" / "generalissimo_input.schema.json"

GT = {"year": 1936, "month": 1, "day": 2, "hour": 15}
WORLD = {
    "own_units": [{"unit_id": 1}, {"unit_id": 2}],
    "armies": [{"army_id": 10, "unit_ids": [1]}],
    "army_groups": [{"army_group_id": 20, "army_ids": [10]}],
    "plans": [{"plan_id": 30}],
    "leaders": [{"leader_id": 40}],
}


def write_input(scope=None):
    return {"meta": {"game_time": GT, "allow_write": True,
                     "geography_scope": scope or {"kind": "global"}},
            "world": copy.deepcopy(WORLD)}


def value_for(name):
    if name.endswith("unit_ids"):
        return [1]
    if name.endswith("army_ids"):
        return [10]
    if name in ("army_id", "to_army_id", "from_army_id", "reassign_unit_ids_to_army_id"):
        return 10
    if name in ("army_group_id", "parent_army_group_id"):
        return 20
    if name in ("plan_id", "parent_frontline_id"):
        return 30
    if name == "leader_id":
        return 40
    if name.endswith("province_ids"):
        return [100]
    if name in ("new_ref",):
        return "r1"
    if name in ("post", "from_post", "to_post"):
        return {"kind": "army", "id": 10}
    if name == "cancel_scope":
        return "current_movement"
    if name in ("keep_armies", "executing"):
        return True
    if name == "ability":
        return "assault_leader"
    raise KeyError(name)


def minimal(cmd_type, seq=1):
    spec = g.COMMANDS[cmd_type]
    cmd = {"order_seq": seq, "type": cmd_type, "subject": {"unit_ids": [1]}}
    for name in spec.get("req", {}):
        cmd[name] = value_for(name)
    for group in spec.get("exactly_one", []) + spec.get("at_least_one", []):
        cmd[group[0]] = value_for(group[0])
    return cmd


def out(orders=(), alerts=(), intents=(), brief=None):
    o = {"orders": list(orders), "alerts": list(alerts), "intents": list(intents)}
    if brief:
        o["brief"] = brief
    return o


class SchemaFile(unittest.TestCase):
    def test_committed_schema_matches_builder(self):
        text = (CALLING / "tables" / "generalissimo_output.schema.json").read_text(encoding="utf-8")
        self.assertEqual(text, g.schema_text())

    def test_schema_is_valid_and_complete(self):
        Draft202012Validator.check_schema(g.build_schema())
        counts = {c: sum(1 for v in g.COMMANDS.values() if v["cat"] == c) for c in g.CATEGORIES}
        self.assertEqual(counts, {"maneuver": 6, "formation": 8, "leaders": 4, "plans": 15,
                                  "tasks": 3})


class EveryCommand(unittest.TestCase):
    def test_each_command_minimal_example_is_accepted(self):
        for t in g.COMMANDS:
            with self.subTest(t=t):
                self.assertEqual(g.validate_output(out([minimal(t)]), write_input()), [])

    def test_unknown_field_rejected(self):
        cmd = minimal("move")
        cmd["speed"] = "5x"
        self.assertTrue(g.validate_output(out([cmd]), write_input()))

    def test_unknown_type_rejected(self):
        cmd = minimal("move")
        cmd["type"] = "build_division"
        self.assertTrue(g.validate_output(out([cmd]), write_input()))


class Gate(unittest.TestCase):
    def test_allow_write_false_requires_empty_orders(self):
        inp = write_input()
        inp["meta"]["allow_write"] = False
        errs = g.validate_output(out([minimal("move")]), inp)
        self.assertIn("allow_write", errs[0]["message"])

    def test_missing_allow_write_counts_as_false(self):
        inp = write_input()
        del inp["meta"]["allow_write"]
        self.assertTrue(g.validate_output(out([minimal("move")]), inp))

    def test_null_scope_blocks_writes(self):
        inp = write_input()
        inp["meta"]["geography_scope"] = None
        errs = g.validate_output(out([minimal("move")]), inp)
        self.assertTrue(any("geography_scope" in e["message"] for e in errs))

    def test_theater_scope_limits_provinces(self):
        inp = write_input({"kind": "theater", "province_ids": [100]})
        self.assertEqual(g.validate_output(out([minimal("move")]), inp), [])
        cmd = minimal("move")
        cmd["target_province_ids"] = [999]
        self.assertTrue(g.validate_output(out([cmd]), inp))

    def test_empty_output_always_ok(self):
        self.assertEqual(g.validate_output(out(), {}), [])


class References(unittest.TestCase):
    def test_unknown_unit_rejected(self):
        cmd = minimal("move")
        cmd["subject"] = {"unit_ids": [999]}
        self.assertTrue(g.validate_output(out([cmd]), write_input()))

    def test_missing_world_collection_rejected(self):
        inp = write_input()
        del inp["world"]["leaders"]
        self.assertTrue(g.validate_output(out([minimal("assign_leader")]), inp))

    def test_ref_chain(self):
        create = minimal("create_army", 1)
        assign = minimal("assign_leader", 2)
        assign["post"] = {"kind": "army_ref", "ref": "r1"}
        self.assertEqual(g.validate_output(out([create, assign]), write_input()), [])
        # ref used before it is created
        self.assertTrue(g.validate_output(out([dict(assign, order_seq=1),
                                               dict(create, order_seq=2)]), write_input()))
        # wrong kind of ref
        assign["post"] = {"kind": "army_group_ref", "ref": "r1"}
        self.assertTrue(g.validate_output(out([create, assign]), write_input()))

    def test_plan_ref_must_match_plan_kind(self):
        front = minimal("create_frontline", 1)
        upd = {"order_seq": 2, "type": "update_offensive_line", "subject": {"unit_ids": [1]},
               "plan_ref": "r1"}
        self.assertTrue(g.validate_output(out([front, upd]), write_input()))
        upd["type"] = "update_frontline"
        self.assertEqual(g.validate_output(out([front, upd]), write_input()), [])

    def test_update_needs_exactly_one_plan_key(self):
        cmd = minimal("update_frontline")
        cmd["plan_ref"] = "x"
        self.assertTrue(g.validate_output(out([cmd]), write_input()))
        del cmd["plan_ref"], cmd["plan_id"]
        self.assertTrue(g.validate_output(out([cmd]), write_input()))

    def test_disband_army_group_must_keep_armies(self):
        cmd = minimal("disband_army_group")
        cmd["keep_armies"] = False
        self.assertTrue(g.validate_output(out([cmd]), write_input()))

    def test_duplicate_seq_rejected(self):
        self.assertTrue(g.validate_output(out([minimal("move", 1), minimal("attack", 1)]),
                                          write_input()))


class IntentsAlertsBrief(unittest.TestCase):
    def test_intent_must_expand_to_real_orders(self):
        intent = {"intent_id": "i1", "kind": "hold_line", "subject": {"unit_ids": [1]},
                  "expands_to_order_seqs": [1]}
        self.assertEqual(g.validate_output(out([minimal("move", 1)], intents=[intent]),
                                           write_input()), [])
        self.assertTrue(g.validate_output(out(intents=[intent]), write_input()))

    def test_alert_payload_checked_by_kind(self):
        bad = {"alert_id": "a", "severity": "high", "kind": "encircled", "message": "m",
               "payload": {"unit_ids": [1]}}
        self.assertTrue(g.validate_output(out(alerts=[bad]), {}))
        bad["payload"]["province_ids"] = [2]
        self.assertEqual(g.validate_output(out(alerts=[bad]), {}), [])

    def test_brief_time_must_match_input(self):
        brief = {"game_time": dict(GT, hour=16), "summary": "s", "stance_applied": "hold_line"}
        self.assertTrue(g.validate_output(out(brief=brief), write_input()))


class FeedbackGap(unittest.TestCase):
    """Documents the known gap: the sealed input schema's feedback type cannot
    name 21 of the 36 output commands (see 陆军总司令函数接口_schema对照.md)."""

    def test_feedback_type_coverage(self):
        s = json.loads(INPUT_SCHEMA.read_text(encoding="utf-8"))
        any_of = s["$defs"]["Feedback"]["properties"]["last_orders"]["items"]["properties"][
            "type"]["anyOf"]
        allowed = set()
        for branch in any_of:
            target = s["$defs"][branch["$ref"].split("/")[-1]] if "$ref" in branch else branch
            allowed |= set(target["enum"])
        missing = set(g.COMMANDS) - allowed
        self.assertEqual(len(missing), 21, sorted(missing))
        self.assertEqual(allowed - set(g.COMMANDS) - {"idle", "garrison", "training", "unknown"},
                         {"reassign_unit"})


class DecideV0(unittest.TestCase):
    def test_fixtures_produce_valid_observe_only_output(self):
        for path in FIXTURES:
            with self.subTest(path=path.name):
                doc = decide_v0.load_input(path, None, True)
                result = decide_v0.decide(doc)
                self.assertEqual(g.validate_output(result, doc), [])
                self.assertEqual(result["orders"], [])
                self.assertEqual(result["intents"], [])
                self.assertEqual(result["brief"]["stance_applied"], "annihilate")
                for alert in result["alerts"]:
                    self.assertNotIn("deficit", alert["payload"])  # never invented

    def test_default_stance_without_policy(self):
        doc = decide_v0.load_input(FIXTURES[0], None, False)
        self.assertEqual(decide_v0.decide(doc)["brief"]["stance_applied"], "preserve_force")

    def test_allow_write_true_still_no_orders(self):
        doc = decide_v0.load_input(FIXTURES[0], None, True)
        doc["meta"]["allow_write"] = True
        self.assertEqual(decide_v0.decide(doc)["orders"], [])

    def test_encirclement_crisis_becomes_critical_alert(self):
        doc = {"meta": {"game_time": GT}, "world": {"own_units": [{"unit_id": 1}],
               "crises": [{"kind": "encircled", "unit_ids": [1], "province_ids": [5],
                           "severity": "critical"}]}}
        result = decide_v0.decide(doc)
        self.assertEqual(g.validate_output(result, doc), [])
        self.assertEqual([(a["kind"], a["severity"]) for a in result["alerts"]],
                         [("encircled", "critical")])

    def test_empty_input(self):
        result = decide_v0.decide({})
        self.assertEqual(result, {"orders": [], "alerts": [], "intents": []})
        self.assertEqual(g.validate_output(result, {}), [])

    def test_no_backend_imported(self):
        for name in BACKEND_MODULES:
            self.assertNotIn(name, sys.modules)


class DecideV1(unittest.TestCase):
    def setUp(self):
        import decide_v1
        self.v1 = decide_v1
        self.doc = decide_v0.load_input(FIXTURES[0], None, True)

    def test_no_orders_without_write_permission(self):
        self.assertEqual(self.v1.decide(self.doc)["orders"], [])

    def test_no_orders_without_scope(self):
        self.doc["meta"]["allow_write"] = True
        self.doc["meta"]["geography_scope"] = None
        self.assertEqual(self.v1.decide(self.doc)["orders"], [])

    def test_reinforces_outnumbered_defence(self):
        self.doc["meta"]["allow_write"] = True
        out = self.v1.decide(self.doc)
        self.assertEqual(g.validate_output(out, self.doc), [])
        world = self.doc["world"]
        nbrs = {p["province_id"]: set(p.get("neighbors", [])) for p in world["provinces"]}
        units = {u["unit_id"]: u for u in world["own_units"]}
        self.assertTrue(out["orders"])
        for o in out["orders"]:
            self.assertEqual(o["type"], "move")
            (uid,), (dest,) = o["subject"]["unit_ids"], o["target_province_ids"]
            self.assertFalse(units[uid].get("in_combat"))
            self.assertIn(dest, nbrs[units[uid]["province_id"]])  # engine-read adjacency
        # 13237: 6 attackers vs 2 defenders -> at most 4 reinforcements
        self.assertLessEqual(sum(o["target_province_ids"] == [13237] for o in out["orders"]), 4)
        self.assertEqual([i["expands_to_order_seqs"] for i in out["intents"]],
                         [[o["order_seq"] for o in out["orders"]]])

    def _battle(self, orgs, stance):
        units = [{"unit_id": i, "province_id": 10, "organization": o, "in_combat": True}
                 for i, o in enumerate(orgs, 1)]
        units.append({"unit_id": 99, "province_id": 11, "organization": 50})
        return {"meta": {"game_time": GT, "allow_write": True,
                         "geography_scope": {"kind": "global"},
                         "player_country": {"index": 44}},
                "policy": {"stance": stance},
                "world": {"own_units": units,
                          "provinces": [{"province_id": 10, "neighbors": [11, 12]},
                                        {"province_id": 11, "neighbors": [10],
                                         "controller": {"index": 44}},
                                        {"province_id": 12, "neighbors": [10],
                                         "controller": {"index": 7}}],
                          "combats": [{"combat_id": 1, "province_id": 10,
                                       "attacker_unit_ids": [500],
                                       "defender_unit_ids": list(range(1, len(orgs) + 1))}]}}

    def test_collapsing_defender_retreats_to_own_province(self):
        doc = self._battle([8.0, 40.0], "preserve_force")
        out = self.v1.decide(doc)
        self.assertEqual(g.validate_output(out, doc), [])
        retreats = [o for o in out["orders"] if o["type"] == "retreat"]
        self.assertEqual([(o["subject"]["unit_ids"], o["to_province_ids"]) for o in retreats],
                         [([1], [11])])  # never 12: not our controller

    def test_stance_sets_threshold(self):
        self.assertFalse([o for o in self.v1.decide(self._battle([15.0, 40.0], "annihilate"))["orders"]
                          if o["type"] == "retreat"])
        self.assertTrue([o for o in self.v1.decide(self._battle([15.0, 40.0], "preserve_force"))["orders"]
                         if o["type"] == "retreat"])

    def _front(self, our_orgs, enemy_orgs, stance="annihilate"):
        units = [{"unit_id": i, "province_id": 20, "organization": o} for i, o in enumerate(our_orgs, 1)]
        vis = [{"unit_id": 900 + i, "province_id": 30, "relation_to_player": "enemy",
                "organization": o} for i, o in enumerate(enemy_orgs)]
        return {"meta": {"game_time": GT, "allow_write": True, "geography_scope": {"kind": "global"},
                         "player_country": {"index": 44}},
                "policy": {"stance": stance},
                "world": {"own_units": units, "visible_units": vis, "combats": [],
                          "provinces": [{"province_id": 20, "neighbors": [30]}]}}

    def test_counterattack_needs_superiority(self):
        doc = self._front([50, 50], [30, 30])          # 100 >= 1.5*60
        out = self.v1.decide(doc)
        self.assertEqual(g.validate_output(out, doc), [])
        self.assertEqual(sorted((o["type"], o["target_province_ids"][0]) for o in out["orders"]),
                         [("attack", 30), ("attack", 30)])
        self.assertFalse(self.v1.decide(self._front([50, 50], [40, 40]))["orders"])   # 100 < 120
        self.assertFalse(self.v1.decide(self._front([50, 50], [30, 30], "preserve_force"))["orders"])
        self.assertFalse(self.v1.decide(self._front([90], [20, 20]))["orders"])       # outnumbered
        self.assertFalse(self.v1.decide(self._front([25, 25, 25], [5]))["orders"])    # too tired

    def test_no_double_retreat_and_no_tired_reinforcements(self):
        doc = self._battle([5.0, 40.0], "annihilate")
        doc["world"]["own_units"][0]["order"] = {"type": "unknown", "target_province_ids": [11],
                                                  "path_province_ids": [11]}
        self.assertFalse([o for o in self.v1.decide(doc)["orders"] if o["type"] == "retreat"])
        doc = self._battle([40.0], "annihilate")
        doc["world"]["combats"][0]["attacker_unit_ids"] = [500, 501, 502]
        doc["world"]["provinces"][1]["neighbors"] = [10]
        doc["world"]["own_units"][-1]["organization"] = 8.0   # tired neighbour stays home
        self.assertFalse([o for o in self.v1.decide(doc)["orders"] if o["type"] == "move"])
        doc["world"]["own_units"][-1]["organization"] = 50.0
        self.assertTrue([o for o in self.v1.decide(doc)["orders"] if o["type"] == "move"])

    def test_surplus_defenders_strike_back(self):
        doc = self._front([50, 45, 40, 35], [20])
        world = doc["world"]
        for u in world["own_units"]:
            u["in_combat"] = True
        world["combats"] = [{"combat_id": 1, "province_id": 20, "attacker_unit_ids": [900],
                             "defender_unit_ids": [1, 2, 3, 4]}]
        # default: defenders never strike out (engine rejected it live)
        self.assertFalse([o for o in self.v1.decide(doc)["orders"] if o["type"] == "attack"])
        self.v1.ALLOW_SURPLUS_STRIKE = True
        self.addCleanup(setattr, self.v1, "ALLOW_SURPLUS_STRIKE", False)
        out = self.v1.decide(doc)
        self.assertEqual(g.validate_output(out, doc), [])
        attackers = sorted(o["subject"]["unit_ids"][0] for o in out["orders"] if o["type"] == "attack")
        self.assertNotIn(1, attackers)          # the strongest defender always stays
        self.assertEqual(attackers, [2, 3, 4])  # 50 >= 1.5*20, the rest are free
        world["combats"][0]["attacker_unit_ids"] = [900, 777]   # one attacker unseen
        self.assertFalse([o for o in self.v1.decide(doc)["orders"] if o["type"] == "attack"])


if __name__ == "__main__":
    unittest.main()
