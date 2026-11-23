"""GeneralissimoOutput contract: JSON schema builder plus semantic checks.

Source: 钢四陆军总司令/陆军总司令函数接口.md (Grok Bot spec, 2026-11-06), section
「输出契约」. This module is the single source of truth for the output shape;
calling/tables/generalissimo_output.schema.json is generated from
build_schema() and a test keeps the two identical.

Pure offline code. It never reads a process, posts a command, or touches a
save. Validation passing means "well-formed and inside the permission gate",
not "the game will accept or execute it".
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "tables" / "generalissimo_output.schema.json"

# ---------------------------------------------------------------- field types
INT = {"type": "integer"}
STR = {"type": "string"}
BOOL = {"type": "boolean"}
NUM = {"type": "number"}
INT_LIST = {"type": "array", "items": INT, "minItems": 1}
INT_LIST_ANY = {"type": "array", "items": INT}  # may be empty (remove/add lists)
REF = {"type": "string", "minLength": 1}
POST = {"$ref": "#/$defs/Post"}

# type -> (category, required fields, optional fields, one_of groups)
# one_of groups: exactly one member of each group must be present.
# at_most_one groups are expressed with the same tuple but flagged "<=1".
_ASSIGN = {"assigned_army_ids": INT_LIST_ANY, "assigned_unit_ids": INT_LIST_ANY}
_UNTIL = {"type": "object", "additionalProperties": False,
          "properties": {"organization": NUM, "experience": NUM}}

COMMANDS: dict[str, dict] = {
    # orders.maneuver
    "move": dict(cat="maneuver", req={"target_province_ids": INT_LIST},
                 opt={"path_province_ids": INT_LIST}),
    "strategic_redeploy": dict(cat="maneuver", req={"target_province_ids": INT_LIST},
                               opt={"path_province_ids": INT_LIST}),
    "attack": dict(cat="maneuver", req={"target_province_ids": INT_LIST}),
    "support_attack": dict(cat="maneuver", req={"target_province_ids": INT_LIST},
                           opt={"supported_unit_ids": INT_LIST}),
    "retreat": dict(cat="maneuver", opt={"to_province_ids": INT_LIST}),
    "cancel": dict(cat="maneuver", req={"cancel_scope": {
        "enum": ["current_movement", "current_combat_order", "all_queued"]}}),
    # orders.formation
    "create_army": dict(cat="formation", req={"new_ref": REF, "unit_ids": INT_LIST},
                        opt={"name": STR, "leader_id": INT,
                             "parent_army_group_id": INT, "parent_army_group_ref": REF},
                        at_most_one=[("parent_army_group_id", "parent_army_group_ref")]),
    "modify_army": dict(cat="formation", req={"army_id": INT},
                        opt={"name": STR, "add_unit_ids": INT_LIST, "remove_unit_ids": INT_LIST,
                             "parent_army_group_id": {"type": ["integer", "null"]}}),
    "disband_army": dict(cat="formation", req={"army_id": INT},
                         opt={"reassign_unit_ids_to_army_id": INT}),
    "create_army_group": dict(cat="formation", req={"new_ref": REF, "army_ids": INT_LIST},
                              opt={"name": STR, "leader_id": INT}),
    "modify_army_group": dict(cat="formation", req={"army_group_id": INT},
                              opt={"name": STR, "add_army_ids": INT_LIST,
                                   "remove_army_ids": INT_LIST}),
    # 宪章: keep_armies 应为 true；只拆群结构，不能借解散把师删掉
    "disband_army_group": dict(cat="formation", req={"army_group_id": INT,
                                                     "keep_armies": {"const": True}}),
    "assign_units": dict(cat="formation", req={"unit_ids": INT_LIST, "to_army_id": INT},
                         opt={"from_army_id": INT}),
    "unassign_units": dict(cat="formation", req={"unit_ids": INT_LIST, "from_army_id": INT}),
    # orders.leaders
    "assign_leader": dict(cat="leaders", req={"leader_id": INT, "post": POST}),
    "unassign_leader": dict(cat="leaders", req={"leader_id": INT, "post": POST}),
    "reassign_leader": dict(cat="leaders", req={"leader_id": INT, "from_post": POST,
                                                "to_post": POST}),
    "use_leader_ability": dict(cat="leaders", req={"leader_id": INT, "ability": REF},
                               opt={"target": {
                                   "type": "object", "additionalProperties": False,
                                   "minProperties": 1,
                                   "properties": {"province_ids": INT_LIST,
                                                  "unit_ids": INT_LIST,
                                                  "combat_id": INT}}}),
    # orders.plans
    "create_frontline": dict(cat="plans", req={"new_ref": REF, "vertex_province_ids": INT_LIST},
                             opt={**_ASSIGN, "execute": BOOL}),
    "update_frontline": dict(cat="plans", opt={"plan_id": INT, "plan_ref": REF,
                                               "vertex_province_ids": INT_LIST, **_ASSIGN},
                             exactly_one=[("plan_id", "plan_ref")]),
    "delete_frontline": dict(cat="plans", req={"plan_id": INT}),
    "create_offensive_line": dict(cat="plans", req={"new_ref": REF,
                                                    "vertex_province_ids": INT_LIST},
                                  opt={"axis_province_ids": INT_LIST,
                                       "parent_frontline_id": INT, "parent_frontline_ref": REF,
                                       **_ASSIGN, "execute": BOOL},
                                  at_most_one=[("parent_frontline_id", "parent_frontline_ref")]),
    "update_offensive_line": dict(cat="plans", opt={"plan_id": INT, "plan_ref": REF,
                                                    "vertex_province_ids": INT_LIST,
                                                    "axis_province_ids": INT_LIST, **_ASSIGN},
                                  exactly_one=[("plan_id", "plan_ref")]),
    "delete_offensive_line": dict(cat="plans", req={"plan_id": INT}),
    "set_plan_execution": dict(cat="plans", req={"plan_id": INT, "executing": BOOL}),
    "assign_to_plan": dict(cat="plans", req={"plan_id": INT},
                           opt={"army_ids": INT_LIST, "unit_ids": INT_LIST},
                           at_least_one=[("army_ids", "unit_ids")]),
    "unassign_from_plan": dict(cat="plans", req={"plan_id": INT},
                               opt={"army_ids": INT_LIST, "unit_ids": INT_LIST},
                               at_least_one=[("army_ids", "unit_ids")]),
    # orders.tasks
    "train": dict(cat="tasks", opt={"until": _UNTIL}),
    "exercise": dict(cat="tasks", opt={"until": _UNTIL}),
    "cancel_task": dict(cat="tasks"),
}
for _kind in ("garrison", "area_defense"):
    COMMANDS["create_" + _kind] = dict(cat="plans", req={"new_ref": REF, "province_ids": INT_LIST},
                                       opt={**_ASSIGN, "execute": BOOL})
    COMMANDS["update_" + _kind] = dict(cat="plans", opt={"plan_id": INT, "plan_ref": REF,
                                                         "province_ids": INT_LIST, **_ASSIGN},
                                       exactly_one=[("plan_id", "plan_ref")])
    COMMANDS["delete_" + _kind] = dict(cat="plans", req={"plan_id": INT})

CATEGORIES = ("maneuver", "formation", "leaders", "plans", "tasks")
INTENT_KINDS = ["concentrate", "split", "seal_pocket", "close_encirclement",
                "fall_back_to_line", "hold_line", "exploit", "relieve_encircled", "custom"]
ALERT_SEVERITIES = ["info", "watch", "high", "critical"]
STANCES = ["preserve_force", "hold_line", "annihilate", "economize_manpower", "custom"]

_ALERT_PAYLOADS = {
    "equipment_shortage": ({"equipment_type": STR},
                           {"deficit": INT, "stockpile": INT, "demanded": INT,
                            "affected_unit_ids": INT_LIST_ANY,
                            "affected_plan_ids": INT_LIST_ANY}),
    "manpower_shortage": ({}, {"available": INT, "needed": INT, "deficit": INT,
                               "affected_unit_ids": INT_LIST_ANY}),
    "missing_divisions": ({"reason": STR}, {"plan_id": INT, "province_ids": INT_LIST_ANY,
                                            "needed_estimate": INT}),
    "major_victory": ({}, {"combat_id": INT, "province_id": INT, "casualties": {"type": "object"}}),
    "major_defeat": ({}, {"combat_id": INT, "province_id": INT, "casualties": {"type": "object"}}),
    "encircled": ({"unit_ids": INT_LIST_ANY, "province_ids": INT_LIST_ANY}, {}),
    "encirclement_imminent": ({"unit_ids": INT_LIST_ANY, "province_ids": INT_LIST_ANY}, {}),
    "plan_failed": ({}, {"plan_id": INT, "failed_order_seqs": INT_LIST_ANY, "error": STR}),
    "insufficient_permission": ({"need": {"enum": ["conscription", "production", "template",
                                                   "doctrine", "focus", "diplomacy", "navy",
                                                   "air", "other"]},
                                 "detail": STR}, {}),
}
ALERT_KINDS = list(_ALERT_PAYLOADS)


def _obj(req: dict, opt: dict | None = None) -> dict:
    props = {**req, **(opt or {})}
    out = {"type": "object", "additionalProperties": False, "properties": props}
    if req:
        out["required"] = sorted(req)
    return out


def _command_schema(name: str, spec: dict) -> dict:
    common_req = {"order_seq": {"type": "integer", "minimum": 0}, "type": {"const": name},
                  "subject": {"$ref": "#/$defs/Subject"}}
    common_opt = {"reason": STR, "replaces_order_seqs": INT_LIST}
    out = _obj({**common_req, **spec.get("req", {})}, {**common_opt, **spec.get("opt", {})})
    rules = []
    for group in spec.get("exactly_one", []):
        rules.append({"oneOf": [{"required": [g]} for g in group]})
    for group in spec.get("at_least_one", []):
        rules.append({"anyOf": [{"required": [g]} for g in group]})
    for group in spec.get("at_most_one", []):
        rules.append({"not": {"required": list(group)}})
    if rules:
        out["allOf"] = rules
    return out


def build_schema() -> dict:
    defs = {
        "GameTime": _obj({k: INT for k in ("year", "month", "day", "hour")}),
        "Subject": {"type": "object", "additionalProperties": False, "minProperties": 1,
                    "properties": {"unit_ids": INT_LIST, "army_ids": INT_LIST,
                                   "army_group_ids": INT_LIST}},
        "Post": {"oneOf": [
            _obj({"kind": {"enum": ["army", "army_group"]}, "id": INT}),
            _obj({"kind": {"enum": ["army_ref", "army_group_ref"]}, "ref": REF})]},
    }
    for name, spec in COMMANDS.items():
        defs["Cmd_" + name] = _command_schema(name, spec)
    alert_variants = []
    for kind, (req, opt) in _ALERT_PAYLOADS.items():
        alert_variants.append({
            "if": {"properties": {"kind": {"const": kind}}, "required": ["kind"]},
            "then": {"properties": {"payload": _obj(req, opt)}}})
    defs["Alert"] = {**_obj({"alert_id": REF, "severity": {"enum": ALERT_SEVERITIES},
                             "kind": {"enum": ALERT_KINDS}, "message": REF,
                             "payload": {"type": "object"}},
                            {"suggested_player_action": STR}),
                     "allOf": alert_variants}
    defs["Intent"] = _obj({"intent_id": REF, "kind": {"enum": INTENT_KINDS},
                           "subject": {"$ref": "#/$defs/Subject"},
                           "expands_to_order_seqs": INT_LIST},
                          {"province_ids": INT_LIST_ANY, "notes": STR})
    defs["Brief"] = _obj({"game_time": {"$ref": "#/$defs/GameTime"}, "summary": REF,
                          "stance_applied": STR},
                         {"fronts": {"type": "array", "items": _obj(
                             {"plan_id": INT, "assessment": STR})},
                          "risks": {"type": "array", "items": STR},
                          "next_watch": {"type": "array", "items": STR}})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "GeneralissimoOutput",
        "$comment": ("Generated by calling/generalissimo_output.py build_schema(); do not edit "
                     "by hand. Source: 陆军总司令函数接口.md 输出契约 (2026-11-06). brief is "
                     "optional because the cadence table marks it 不送 on hourly ticks. "
                     "Shape validity is not proof the game accepts or executes a command."),
        "type": "object", "additionalProperties": False,
        "required": ["orders", "alerts", "intents"],
        "properties": {
            "orders": {"type": "array", "items": {"oneOf": [
                {"$ref": "#/$defs/Cmd_" + n} for n in COMMANDS]}},
            "alerts": {"type": "array", "items": {"$ref": "#/$defs/Alert"}},
            "brief": {"$ref": "#/$defs/Brief"},
            "intents": {"type": "array", "items": {"$ref": "#/$defs/Intent"}},
        },
        "$defs": defs,
    }


def schema_text() -> str:
    return json.dumps(build_schema(), ensure_ascii=False, indent=2) + "\n"


# ------------------------------------------------------------ semantic checks
class OutputError(ValueError):
    pass


def _ids(items, key):
    return {x[key] for x in items or [] if isinstance(x, dict) and key in x}


def _issue(errors, path, msg):
    errors.append({"path": path, "message": msg})


def _provinces_in(cmd: dict) -> set[int]:
    out: set[int] = set()
    for key in ("target_province_ids", "path_province_ids", "to_province_ids",
                "vertex_province_ids", "axis_province_ids", "province_ids"):
        out.update(cmd.get(key, []))
    tgt = cmd.get("target")
    if isinstance(tgt, dict):
        out.update(tgt.get("province_ids", []))
    return out


def semantic_errors(output: dict, input_doc: dict | None) -> list[dict]:
    """Checks the schema cannot express. input_doc is the GeneralissimoInput
    (meta/policy/world/feedback); it may be partial. Missing meta.allow_write
    counts as false (spec default)."""
    errors: list[dict] = []
    inp = input_doc or {}
    meta = inp.get("meta", {}) or {}
    world = inp.get("world", {}) or {}
    orders = output.get("orders", [])
    allow_write = meta.get("allow_write") is True

    # 闸门：allow_write 为 false 时 orders 必须为空数组
    if orders and not allow_write:
        _issue(errors, "orders", "meta.allow_write is not true; orders must be empty")

    # 地理范围未定时不能假设排他指挥权
    scope = meta.get("geography_scope")
    if orders and allow_write:
        if not isinstance(scope, dict):
            _issue(errors, "orders", "geography_scope is null/missing; writes not permitted")
        elif scope.get("kind") == "theater":
            allowed = set(scope.get("province_ids", []))
            for i, cmd in enumerate(orders):
                outside = sorted(_provinces_in(cmd) - allowed)
                if outside:
                    _issue(errors, f"orders/{i}", f"provinces outside theater scope: {outside}")

    # order_seq unique; new_ref unique; refs must point to an earlier new_ref of the right kind
    seqs: list[int] = [c.get("order_seq") for c in orders]
    if len(seqs) != len(set(seqs)):
        _issue(errors, "orders", "duplicate order_seq")
    refs: dict[str, str] = {}
    for i, cmd in enumerate(orders):
        t = cmd.get("type", "")
        plan_want = "create_" + t.split("_", 1)[1] if t.startswith("update_") else None
        for key, want in (("parent_army_group_ref", "create_army_group"),
                          ("parent_frontline_ref", "create_frontline"),
                          ("plan_ref", plan_want)):
            if key in cmd:
                made_by = refs.get(cmd[key])
                if made_by is None:
                    _issue(errors, f"orders/{i}/{key}", "ref not created earlier in this output")
                elif made_by != want:
                    _issue(errors, f"orders/{i}/{key}", f"ref was made by {made_by}, not {want}")
        for key in ("post", "from_post", "to_post"):
            post = cmd.get(key)
            if isinstance(post, dict) and "ref" in post:
                want = "create_army" if post.get("kind") == "army_ref" else "create_army_group"
                if refs.get(post["ref"]) != want:
                    _issue(errors, f"orders/{i}/{key}", f"ref must name an earlier {want}")
        if "new_ref" in cmd:
            if cmd["new_ref"] in refs:
                _issue(errors, f"orders/{i}/new_ref", "duplicate new_ref")
            refs[cmd["new_ref"]] = t
        if cmd.get("order_seq") in cmd.get("replaces_order_seqs", []):
            _issue(errors, f"orders/{i}", "order replaces itself")

    # references must exist in the input (unit_ids 必须是已存在的己方陆军实体)
    if orders:
        known = {
            "unit": _ids(world.get("own_units"), "unit_id"),
            "army": _ids(world.get("armies"), "army_id"),
            "army_group": _ids(world.get("army_groups"), "army_group_id"),
            "plan": _ids(world.get("plans"), "plan_id"),
            "leader": _ids(world.get("leaders"), "leader_id"),
        }
        present = {
            "unit": "own_units" in world, "army": "armies" in world,
            "army_group": "army_groups" in world, "plan": "plans" in world,
            "leader": "leaders" in world,
        }

        def check(kind, ids, path):
            if not present[kind]:
                _issue(errors, path, f"input has no world collection for {kind}; "
                                     "reference cannot be verified")
                return
            missing = sorted(set(ids) - known[kind])
            if missing:
                _issue(errors, path, f"unknown {kind} ids {missing}")

        for i, cmd in enumerate(orders):
            subj = cmd.get("subject", {})
            for key, kind in (("unit_ids", "unit"), ("army_ids", "army"),
                              ("army_group_ids", "army_group")):
                if key in subj:
                    check(kind, subj[key], f"orders/{i}/subject/{key}")
            for key, kind in (("unit_ids", "unit"), ("add_unit_ids", "unit"),
                              ("remove_unit_ids", "unit"), ("supported_unit_ids", "unit"),
                              ("assigned_unit_ids", "unit"), ("army_ids", "army"),
                              ("add_army_ids", "army"), ("remove_army_ids", "army"),
                              ("assigned_army_ids", "army")):
                if key in cmd:
                    check(kind, cmd[key], f"orders/{i}/{key}")
            for key, kind in (("army_id", "army"), ("to_army_id", "army"),
                              ("from_army_id", "army"), ("reassign_unit_ids_to_army_id", "army"),
                              ("army_group_id", "army_group"),
                              ("parent_army_group_id", "army_group"),
                              ("plan_id", "plan"), ("parent_frontline_id", "plan"),
                              ("leader_id", "leader")):
                if isinstance(cmd.get(key), int):
                    check(kind, [cmd[key]], f"orders/{i}/{key}")
            for key in ("post", "from_post", "to_post"):
                post = cmd.get(key)
                if isinstance(post, dict) and "id" in post:
                    check(post["kind"], [post["id"]], f"orders/{i}/{key}/id")

    # intents must expand to real orders of this output
    seqset = set(seqs)
    for i, intent in enumerate(output.get("intents", [])):
        bad = sorted(set(intent.get("expands_to_order_seqs", [])) - seqset)
        if bad:
            _issue(errors, f"intents/{i}", f"expands_to_order_seqs not in this output: {bad}")

    # brief.game_time must equal input game_time
    brief = output.get("brief")
    if brief and "game_time" in meta and brief.get("game_time") != meta["game_time"]:
        _issue(errors, "brief/game_time", "differs from input meta.game_time")

    ids = [a.get("alert_id") for a in output.get("alerts", [])]
    if len(ids) != len(set(ids)):
        _issue(errors, "alerts", "duplicate alert_id")
    return errors


def validate_output(output: dict, input_doc: dict | None) -> list[dict]:
    """Schema + semantic errors; empty list means accepted."""
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(build_schema())
    errors = [{"path": "/".join(str(p) for p in e.absolute_path), "message": e.message}
              for e in sorted(validator.iter_errors(output), key=lambda e: list(e.absolute_path))]
    if not errors:
        errors = semantic_errors(output, input_doc)
    return errors


if __name__ == "__main__":  # regenerate the committed schema file
    SCHEMA_PATH.write_text(schema_text(), encoding="utf-8", newline="\n")
    print("wrote", SCHEMA_PATH)
