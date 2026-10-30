"""Read-only proven command / action field layouts (Windows HOI4 1.19.4).

Does not allocate in-game objects or post commands.
"""
from __future__ import annotations

# --- CCommand base (common header stamped by Post) ---
BASE = {
    "name": "CCommand",
    "fields": {
        "vt": 0x0,
        "refcount_or_pad": 0x8,
        "tick": 0xC,  # Post stamps from session+0x84
        "word_0x18": 0x18,  # Post stamps min(session+0x60, 0x7fff)
        "execlist_select": 0x1A,
        "sink_seq": 0x1C,
    },
    "vt_slots": {
        "IsValid": 0x48,
        "Execute": 0x50,
        "PostExec": 0x58,  # often type-id writer
        "gate_0x60": 0x60,  # early Post gate (TRUE=0x188d90 / FALSE=0x11d530)
        "Clone": 0x68,
        "gate_0x80": 0x80,  # early Post gate
        "auth_0x90": 0x90,  # "sender not authorized"
        "serialize_payload": 0xA0,
    },
    "shared_serialize_header_write": 0x22D9390,  # vt+0x10
    "shared_serialize_header_read": 0x22D90F0,  # vt+0x20
}

POST_GATES = {
    "FN_CMD_QUEUE_POST": 0x22C41E0,
    "order": [
        "r8b != 0 (caller force)",
        "session+0x725 != 0 (live SP often 1)",
        "cmd.vt+0x80 TRUE OR cmd.vt+0x60 TRUE",
    ],
    "else_drop": "Dropped command:",
    "during_exec_drop": "session+0x6CC && !session+0x726 -> Dropped (posted during command execution)",
    "auth_drop": "cmd.vt+0x90 fail -> Dropped (sender not authorized)",
    "gate_stub_TRUE": 0x188D90,
    "gate_stub_FALSE": 0x11D530,  # xor al,al; ret
    "CMoveCommand_gate": "vt+0x60 AND vt+0x80 both FALSE — needs session+0x725 or r8b",
    "never_post_speed": ["CSetGameSpeedCommand", "CIncreaseGameSpeedCommand", "CDecreaseGameSpeedCommand", "CHourlyTickCommand"],
}

MOVE = {
    "name": "CMoveCommand",
    "vt": 0x2A2C790,
    "type_id": 0x28A2,
    "size": 0x88,
    "factory": 0x13FB000,
    "clone": 0x13F9350,
    "execute": 0x13FC990,  # thunk -> action.vt+0x48
    "isvalid": 0x14002F0,  # thunk -> action.vt+0x50
    "action_embed": 0x28,
    "gate_0x60": False,
    "gate_0x80": False,
    "action": {
        "name": "CUnitMoveAction",
        "vt": 0x2A1F648,
        "type_id_at_plus8": 0x3648,
        "execute": 0x12C2670,
        "isvalid": 0x12C2CA0,
        "serialize": 0x12C3920,  # action.vt+0xc0
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
        "serialize_tokens": {
            0x10: 0x28A3,
            0x18: 0x2840,
            0x30: 0x174,
            0x50: 0x29F1,
            0x51: 0x2C84,
            0x52: 0x3A98,
            0x53: 0x38F1,
            0x55: 0x2C85,
            0x58: 0x37BC,
            0x5C: 0x368F,
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
    "size": 0x48,
    "execute": 0x13FBBD0,
    "fields": {
        "units_data": 0x28,
        "units_count": 0x34,
        "sticky": 0x40,
    },
}

STARTGAME = {
    "name": "CStartGameCommand",
    "vt": 0x2A5F448,
    "type_id": 0x359E,
    "sticky_session_off": 0xF8,  # wrapper; +0 -> cmd*
    "note": "Live sticky post-exec sample on paused SP (Phase 2bl)",
}

CHAT = {
    "name": "CChatCommand",
    "vt": 0x2A27F28,
    "type_id": 0x184,
    "size": 0x98,
    "factory": 0x13CA430,
    "execute": 0x13CAEE0,
    "gate_0x60": False,
    "gate_0x80": True,
    "fields": {
        "message_sso": 0x28,
        "chat_localize_on_receipt": 0x60,
        "user": 0x64,
        "channel": 0x68,
        "color": 0x6C,
        "receiver": 0x70,
        "datetime": 0x74,
        "sender_sso": 0x78,
    },
}

# Army / order commands (Phase 2ar) — sizes from Clone alloc immediates
ORDERS = {
    "COrderExecuteCommand": {
        "vt": 0x2A85468, "type_id": 0x3040, "size": 0x38,
        "clone": 0x18CDBD0, "serialize": 0x18E87C0, "deserialize": 0x18E2100, "execute": 0x18D6430,
        "fields": {"order_index": 0x30, "execute_order": 0x34, "all": 0x35},
    },
    "COrderAssignCommand": {
        "vt": 0x2A84498, "type_id": 0x303E, "size": 0x50,
        "clone": 0x18CD5B0, "serialize": 0x18E80F0, "deserialize": 0x18E1A70, "execute": 0x18D41B0,
        "fields": {"units_data": 0x28, "units_count": 0x34, "order_index": 0x48, "assign_to_minimum_order": 0x4C},
    },
    "COrderUnassignCommand": {
        "vt": 0x2A84550, "type_id": 0x304D, "size": 0x50,
        "clone": 0x18CEBB0, "serialize": 0x18E91B0, "deserialize": 0x18E2EE0, "execute": 0x18DB050,
        "fields": {"units_data": 0x28, "units_count": 0x34, "unassign_group": 0x48, "unassign_army_group_instances": 0x49},
    },
    "COrderDeleteCommand": {
        "vt": 0x2A843E0, "type_id": 0x303F, "size": 0x38,
        "clone": 0x18CDA90, "serialize": 0x18E86E0, "deserialize": 0x18E1FE0, "execute": 0x18D5FE0,
        "fields": {"order_index": 0x30},
    },
    "COrderNewFrontCommand": {
        "vt": 0x2A84B10, "type_id": 0x3327, "size": 0x70,
        "clone": 0x18CE0E0, "serialize": 0x18E8AF0, "deserialize": 0x18E25C0, "execute": 0x18D9000,
        "fields": {
            "sub_group": 0x30, "units_data": 0x38, "units_count": 0x44,
            "path": 0x50, "attach": 0x68, "split_from": 0x6C, "blitz": 0x6D, "withdraw": 0x6E,
        },
    },
    "COrderNewRootCommand": {
        "vt": 0x2A84DF0, "type_id": 0x3328, "size": 0x70,
        "clone": 0x18CE200, "serialize": 0x18E8BF0, "deserialize": 0x18E26D0, "execute": 0x18D99C0,
    },
    "COrderNewFallbackCommand": {
        "vt": 0x2A84C80, "type_id": 0x33D7, "size": 0x60,
        "clone": 0x18CDFF0, "serialize": 0x18E8A60, "deserialize": 0x18E2500, "execute": 0x18D8FC0,
    },
    "COrderGroupCommand": {
        "vt": 0x2A83D68, "type_id": 0x2ECF, "size": 0x60,
        "clone": 0x18CDC70, "serialize": 0x18E8830, "deserialize": 0x18E21D0, "execute": 0x18D64F0,
        "fields": {"theatre": 0x48, "theater_group": 0x50, "army_group": 0x58},
    },
    "CArmyGroupCommand": {
        "vt": 0x2A83ED8, "type_id": 0x3861, "size": 0x80,
        "clone": 0x18CCCC0, "serialize": 0x18E7A50, "deserialize": 0x18E0E60, "execute": 0x18D25D0,
    },
    "CSetArmyLeaderCommand": {
        "vt": 0x2A85520, "type_id": 0x3051, "size": 0x40,
        "clone": 0x18CEF00, "serialize": 0x18E9390, "deserialize": 0x18E3210, "execute": 0x18DB2C0,
        "fields": {"leader": 0x28, "deploy_army_hq": 0x38},
    },
}

# Army / province helpers (move subject resolve) — RO proven 17/17 HAI
ARMY_MOVE_SUBJECTS = {
    "FN_HANDLE_RESOLVE": 0x2284800,
    "HANDLE_TYPE_ARMY": 0x33,
    "CArmy_handle_off": 0x18,
    "CArmy_province_id_off": 0x28,
    "CProvince_id_off": 0xA4,
    "FN_PROVINCE_RESOLVE": 0xC5A9E0,  # GS thunk
    "note": "Build Move action unit_handle from CArmy+0x18; province path from CArmy+0x28 / resolve",
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
    "dummy_ring": 0xA0,
    "dummy_pending": 0x58,
    "dummy_execlist": 0x40,
    "dummy_seq": 0xD0,
}


def summarize() -> dict:
    return {
        "posting": "DISABLED",
        "pipeline": PIPELINE,
        "post_gates": POST_GATES,
        "base": BASE,
        "move": MOVE,
        "strategic": STRATEGIC,
        "cancel": CANCEL,
        "startgame": STARTGAME,
        "chat": CHAT,
        "orders": {k: {"vt": hex(v["vt"]), "type_id": hex(v["type_id"]), "size": hex(v["size"])} for k, v in ORDERS.items()},
        "army_move_subjects": ARMY_MOVE_SUBJECTS,
    }
