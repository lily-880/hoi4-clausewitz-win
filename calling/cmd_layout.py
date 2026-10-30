"""Read-only proven command / action field layouts (Windows HOI4 1.19.4).

Does not allocate in-game objects or post commands.
"""
from __future__ import annotations

MOVE = {
    "name": "CMoveCommand",
    "vt": 0x2A2C790,
    "type_id": 0x28A2,
    "size": 0x88,
    "factory": 0x13FB000,
    "clone": 0x13F9350,
    "execute": 0x13FC990,  # thunk -> action.vt+0x48
    "action_embed": 0x28,
    "action": {
        "name": "CUnitMoveAction",
        "vt": 0x2A1F648,
        "execute": 0x12C2670,
        "fields": {
            "unit_handle": 0x10,
            "province_arr": 0x18,
            "province_size": 0x24,
            "path_arr": 0x30,
            "path_size": 0x3C,
            "clear": 0x50,
            "safe": 0x51,
            "safe_until_end": 0x52,
            "safe_nonsafe_fb": 0x53,
            "avoid": 0x55,
            "move_priority": 0x58,
            "sticky": 0x5C,
        },
    },
}

STRATEGIC = {
    "name": "CStrategicRedeploymentCommand",
    "vt": 0x2A2D818,
    "type_id": 0x35B9,
    "size": 0x50,
    "factory": 0x13FB580,
    "execute": 0x13FC990,  # shared thunk
    "action_embed": 0x28,
    "action": {
        "name": "CUnitStrategicMoveAction",
        "vt": 0x2A1F7E8,
        "type_id": 0x364A,
        "size": 0x28,
        "serialize": 0x12C3AA0,
        "deserialize": 0x12C3740,
        "fields": {
            "army_handle": 0x10,
            "province": 0x18,
            "clear": 0x1C,
            "move_priority": 0x20,
        },
    },
}

CANCEL = {
    "name": "CCancelMovementCommand",
    "vt": 0x2A2C9B8,
    "type_id": 0x28AF,
    "execute": 0x13FBBD0,
    "fields": {
        "units_data": 0x28,
        "units_count": 0x34,
        "sticky": 0x40,
    },
}

PIPELINE = {
    "post": 0x22C41E0,
    "sink_dummy": 0x23F5CD0,
    "drain_dummy": 0x23F64E0,
    "session_update": 0x22C6410,
    "execute_site_a": 0x22C6C9D,
    "execute_loop_b": 0x22C4710,
    "g_session": 0x34FFBE8,
    "cmd_vt_execute": 0x50,
    "cmd_vt_isvalid": 0x48,
    "cmd_vt_clone": 0x68,
}


def summarize() -> dict:
    return {
        "posting": "DISABLED",
        "pipeline": PIPELINE,
        "move": MOVE,
        "strategic": STRATEGIC,
        "cancel": CANCEL,
    }
