"""Explicit commander geography and stance config.

This module only reads a JSON file and copies two schema-shaped values.
It does not read memory, post orders, write a process, or choose a battle plan.
Null is not rewritten to global. A missing stance is not filled with any enum
member. policy.instructions is never created here.

calling/input_capture_live.py remains the pinned memory observation assembler
and does not call this module. Its sealed hash must stay unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PATH = HERE / "tables" / "commander_policy.json"
SCHEMA_PATH = HERE / "tables" / "generalissimo_input.schema.json"

_MISSING = object()
_FILE_KEYS = {"record", "statement", "geography_scope", "policy"}


class CommanderConfigError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _is_int(value) -> bool:
    return type(value) is int


def _geography(value, schema: dict) -> dict:
    if value is _MISSING:
        raise CommanderConfigError(
            "missing_geography_scope",
            "geography_scope is absent; global is not assumed",
        )
    if value is None:
        raise CommanderConfigError(
            "null_geography_scope",
            "geography_scope null is not global",
        )
    if not isinstance(value, dict):
        raise CommanderConfigError("illegal_geography_scope", "geography_scope must be an object")
    branches = schema["properties"]["meta"]["properties"]["geography_scope"]["anyOf"]
    global_branch = branches[1]
    theater_branch = branches[2]
    kind = value.get("kind", _MISSING)
    if kind == global_branch["properties"]["kind"]["enum"][0]:
        if set(value) != {"kind"}:
            raise CommanderConfigError(
                "conflicting_geography_scope",
                "global scope cannot carry province ids or extra keys",
            )
        return {"kind": kind}
    if kind == theater_branch["properties"]["kind"]["enum"][0]:
        if set(value) != {"kind", "province_ids"}:
            raise CommanderConfigError(
                "illegal_geography_scope",
                "theater scope requires only kind and province_ids",
            )
        ids = value["province_ids"]
        if not isinstance(ids, list) or any(not _is_int(item) for item in ids):
            raise CommanderConfigError(
                "illegal_geography_scope",
                "theater province_ids must be integers",
            )
        return {"kind": kind, "province_ids": list(ids)}
    raise CommanderConfigError("illegal_geography_scope", "geography_scope kind is not in the schema")


def _stance(policy, schema: dict) -> str:
    if policy is _MISSING or not isinstance(policy, dict):
        raise CommanderConfigError(
            "missing_stance",
            "policy.stance is absent; no stance is assumed",
        )
    if set(policy) - {"stance"}:
        raise CommanderConfigError(
            "instructions_not_accepted",
            "this config accepts stance only and does not carry instructions",
        )
    if "stance" not in policy:
        raise CommanderConfigError(
            "missing_stance",
            "policy.stance is absent; no stance is assumed",
        )
    stance = policy["stance"]
    allowed = schema["properties"]["policy"]["properties"]["stance"]["enum"]
    if type(stance) is not str or stance not in allowed:
        raise CommanderConfigError("illegal_stance", "policy.stance is not a schema enum")
    return stance


def load_commander_policy(path: Path | str | None = None) -> dict:
    """Return only meta.geography_scope and policy.stance from an explicit file."""
    source = Path(path) if path is not None else DEFAULT_PATH
    if not source.is_file():
        raise CommanderConfigError("missing_file", "commander policy file is absent")
    try:
        doc = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CommanderConfigError("illegal_file", "commander policy file is not JSON") from exc
    if not isinstance(doc, dict):
        raise CommanderConfigError("illegal_file", "commander policy file has unexpected keys")
    if "allow_write" in doc:
        raise CommanderConfigError("illegal_file", "commander policy cannot grant write permission")
    if set(doc) - _FILE_KEYS:
        raise CommanderConfigError("illegal_file", "commander policy file has unexpected keys")
    schema = _schema()
    scope = _geography(doc.get("geography_scope", _MISSING), schema)
    stance = _stance(doc.get("policy", _MISSING), schema)
    return {"meta": {"geography_scope": scope}, "policy": {"stance": stance}}


def merge_commander_policy(observation: dict, path: Path | str | None = None) -> dict:
    """Copy the saved scope and stance onto an observation without replacing conflicts.

    A missing key is filled from the file. Null, a different kind, or a different
    stance is a conflict and is left unchanged by raising. Instructions, feedback,
    allow_write, and complete_input are not written.
    """
    if not isinstance(observation, dict):
        raise CommanderConfigError("illegal_observation", "observation must be an object")
    saved = load_commander_policy(path)
    out = dict(observation)
    meta = out.get("meta", _MISSING)
    if meta is _MISSING:
        meta = {}
    elif not isinstance(meta, dict):
        raise CommanderConfigError("illegal_observation", "meta must be an object")
    else:
        meta = dict(meta)
    current_scope = meta.get("geography_scope", _MISSING)
    saved_scope = saved["meta"]["geography_scope"]
    if current_scope is _MISSING:
        meta["geography_scope"] = saved_scope
    elif current_scope != saved_scope:
        raise CommanderConfigError(
            "conflicting_geography_scope",
            "observation geography_scope conflicts with the saved config",
        )
    out["meta"] = meta

    policy = out.get("policy", _MISSING)
    if policy is _MISSING:
        policy = {}
    elif not isinstance(policy, dict):
        raise CommanderConfigError("illegal_observation", "policy must be an object")
    else:
        policy = dict(policy)
    current_stance = policy.get("stance", _MISSING)
    saved_stance = saved["policy"]["stance"]
    if current_stance is _MISSING:
        policy["stance"] = saved_stance
    elif current_stance != saved_stance:
        raise CommanderConfigError(
            "conflicting_stance",
            "observation stance conflicts with the saved config",
        )
    out["policy"] = policy
    return out
