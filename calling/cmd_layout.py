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
    "serialize": 0x1404590,  # vt+0xa0 thunk -> action
    "deserialize": 0x1403570,  # vt+0xa8
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
    "factory": 0x13FACE0,
    "serialize": 0x1404130,
    "deserialize": 0x1402D50,
    "execute": 0x13FBBD0,
    "gate_0x60": False,
    "gate_0x80": False,
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
    "serialize": 0x13D7FA0,
    "deserialize": 0x13CF1B0,
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
        "factory": 0x18d0070,
        "vt": 0x2A85468, "type_id": 0x3040, "size": 0x38,
        "clone": 0x18CDBD0, "serialize": 0x18E87C0, "deserialize": 0x18E2100, "execute": 0x18D6430,
        "fields": {"order_index": 0x30, "execute_order": 0x34, "all": 0x35},
    },
    "COrderAssignCommand": {
        "factory": 0x18cfca0,
        "vt": 0x2A84498, "type_id": 0x303E, "size": 0x50,
        "clone": 0x18CD5B0, "serialize": 0x18E80F0, "deserialize": 0x18E1A70, "execute": 0x18D41B0,
        "fields": {"units_data": 0x28, "units_count": 0x34, "order_index": 0x48, "assign_to_minimum_order": 0x4C},
    },
    "COrderUnassignCommand": {
        "factory": 0x18d09b0,
        "vt": 0x2A84550, "type_id": 0x304D, "size": 0x50,
        "clone": 0x18CEBB0, "serialize": 0x18E91B0, "deserialize": 0x18E2EE0, "execute": 0x18DB050,
        "fields": {"units_data": 0x28, "units_count": 0x34, "unassign_group": 0x48, "unassign_army_group_instances": 0x49},
    },
    "COrderDeleteCommand": {
        "factory": 0x18cffa0,
        "vt": 0x2A843E0, "type_id": 0x303F, "size": 0x38,
        "clone": 0x18CDA90, "serialize": 0x18E86E0, "deserialize": 0x18E1FE0, "execute": 0x18D5FE0,
        "fields": {"order_index": 0x30},
    },
    "COrderNewFrontCommand": {
        "factory": 0x18d0340,
        "vt": 0x2A84B10, "type_id": 0x3327, "size": 0x70,
        "clone": 0x18CE0E0, "serialize": 0x18E8AF0, "deserialize": 0x18E25C0, "execute": 0x18D9000,
        "fields": {
            "sub_group": 0x30, "units_data": 0x38, "units_count": 0x44,
            "path": 0x50, "attach": 0x68, "split_from": 0x6C, "blitz": 0x6D, "withdraw": 0x6E,
        },
    },
    "COrderNewRootCommand": {
        "factory": 0x18d03d0,
        "vt": 0x2A84DF0, "type_id": 0x3328, "size": 0x70,
        "clone": 0x18CE200, "serialize": 0x18E8BF0, "deserialize": 0x18E26D0, "execute": 0x18D99C0,
    },
    "COrderNewFallbackCommand": {
        "factory": 0x18d02c0,
        "vt": 0x2A84C80, "type_id": 0x33D7, "size": 0x60,
        "clone": 0x18CDFF0, "serialize": 0x18E8A60, "deserialize": 0x18E2500, "execute": 0x18D8FC0,
    },
    "COrderGroupCommand": {
        "factory": 0x18d00d0,
        "vt": 0x2A83D68, "type_id": 0x2ECF, "size": 0x60,
        "clone": 0x18CDC70, "serialize": 0x18E8830, "deserialize": 0x18E21D0, "execute": 0x18D64F0,
        "fields": {"theatre": 0x48, "theater_group": 0x50, "army_group": 0x58},
    },
    "CArmyGroupCommand": {
        "factory": 0x18cf710,
        "vt": 0x2A83ED8, "type_id": 0x3861, "size": 0x80,
        "clone": 0x18CCCC0, "serialize": 0x18E7A50, "deserialize": 0x18E0E60, "execute": 0x18D25D0,
    },
    "CSetArmyLeaderCommand": {
        "factory": 0x18d0ba0,
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



FACTORY_TABLE = {
    "rva": 0x35011E0,
    "lookup": 0x22D8D20,  # if tid>=0x2710: idx=tid-0x2328; else idx=tid; jmp qword [table+idx*8]
    "recreate": 0x22D8AD0,
    "index_bias_sub_if_ge": 0x2710,  # 10000
    "index_bias": 0x2328,  # 9000; lea eax,[rcx-0x2328]; cmovge
    "max_index": 0x2AF7,  # 10999
    "non_null_live": 456,  # phase2bo RO count
    "note": (
        "Dummy Post serialize→recreate uses this table; hand-built cmds must round-trip. "
        "Dual encoding: for idx<0x2710 both tid=idx and tid=idx+0x2328 hit same slot; "
        "catalog type_ids prefer the biased form when GetTypeId/imm uses it (e.g. Move 0x28a2)."
    ),
}

# vt+0x48 IsValid paths (wrap 0x22d8ea0 → call [vt+0x48]); RO docs only
ISVALID_PATHS = {
    "wrap": 0x22D8EA0,  # save/restore guard then call [rcx.vt+0x48]
    "session_auth_skip_off": 0x3C,  # live SP session+0x3c==1 (auth-skip hyp; not a Post enable)
    "CMoveCommand": {
        "vt_off": 0x48,
        "rva": 0x14002F0,  # thunk: rcx+=0x28; jmp [action.vt+0x50]
        "action_isvalid": 0x12C2CA0,
        "kind": "FN",
        "notes": "Requires valid CUnitMoveAction embed@+0x28; unit handle + province/path vectors",
    },
    "CStrategicRedeploymentCommand": {
        "rva": 0x1402260,
        "kind": "FN",
        "notes": "Army handle@+0x10 + dest province@+0x18",
    },
    "CCancelMovementCommand": {
        "rva": 0x13FED40,
        "kind": "FN",
        "notes": "Walks units vector@+0x28 count@+0x34; empty → fail",
    },
    "COrderExecuteCommand": {
        "rva": 0x18DEF40,
        "kind": "FN",
        "notes": "Subject@+0x28 non-zero pair; order object resolve",
    },
    "CPauseGame": {
        "rva": 0x188D90,  # mov al,1; ret
        "kind": "TRUE",
        "notes": "Always-valid — NEVER_POST; pause/unpause is speed-adjacent",
    },
}

# Remaining army/order-adjacent subtypes (RTTI+factory RO stubs; not full serialize proof)
# type_id = preferred biased form when dual-encoded
REMAINING_ARMY_ORDERS = {
    "CMassMoveCommand": {"type_id": 0x341F, "factory": 0x13FAEC0, "vt": 0x2A2C848, "factory_idx": 4343},
    "CMassCancelMovementCommand": {"type_id": 0x3630, "factory": 0x11D8FD0, "vt": 0x2A0FC40, "factory_idx": 4872},
    "CToggleStrategicDeploymentCommand": {"type_id": 0x3CE0, "factory": 0x13FB640, "vt": 0x2A2CA70, "factory_idx": 6584},
    "COrderSetPathCommand": {"type_id": 0x3039, "factory": 0x18D08E0, "vt": 0x2A84778, "factory_idx": 3345},
    "CDeleteOrderGroupCommand": {"type_id": 0x304E, "factory": 0x18CF9E0, "vt": 0x2A83E20, "factory_idx": 3366},
    "COrderDeleteAllCommand": {"type_id": 0x33F1, "factory": 0x18CFED0, "vt": 0x2A84270, "factory_idx": 4297},
    "COrderInsertFrontCommand": {"type_id": 0x3398, "factory": 0x18D0150, "vt": 0x2A84A58, "factory_idx": 4208},
    "COrderReshapeCommand": {"type_id": 0x339E, "factory": 0x18D06C0, "vt": 0x2A84830, "factory_idx": 4214},
    "COrderConnectCommand": {"type_id": 0x33B1, "factory": 0x18CFE00, "vt": 0x2A849A0, "factory_idx": 4233},
    "COrderReconnectCommand": {"type_id": 0x33B0, "factory": 0x18D0470, "vt": 0x2A848E8, "factory_idx": 4232},
    "CAutoMergeOrdersCommand": {"type_id": 0x3552, "factory": 0x18CF910, "vt": 0x2A84BC8, "factory_idx": 4650},
    "CAssignToArmyGroupCommand": {"type_id": 0x3886, "factory": 0x18CF8A0, "vt": 0x2A83F90, "factory_idx": 5470},
    "CRemoveFromArmyGroupCommand": {"type_id": 0x3887, "factory": 0x18D0A80, "vt": 0x2A84048, "factory_idx": 5471},
    "CDeployArmyHqCommand": {"type_id": 0x282B, "factory": 0x13FAE60, "vt": 0x2A2CEC0, "factory_idx": 1283},
    "CWithdrawArmyHqCommand": {"type_id": 0x2833, "factory": 0x13FB710, "vt": 0x2A2CF78, "factory_idx": 1291},
}

NEVER_POST = {
    "CIncreaseGameSpeedCommand": {
        "vt": 0x29F37C8, "execute": 0xF85930, "type_id": 0x28D7, "factory": 0xF84830,
        "reason": "speed/5x ban",
    },
    "CDecreaseGameSpeedCommand": {
        "vt": 0x29F3880, "execute": 0xF853F0, "type_id": 0x28D8, "factory": 0xF84780,
        "reason": "speed/5x ban",
    },
    "CSetGameSpeedCommand": {
        "vt": 0x29F3938, "execute": 0xF85B50, "type_id": 0x2F42, "factory": 0xF84880,
        "reason": "speed/5x ban",
    },
    "CHourlyTickCommand": {
        "vt": 0x29F3710, "execute": 0xF85630, "type_id": 0x2F3C, "factory": 0xF847E0,
        "reason": "hourly/speed ban",
    },
    "CSendPingCommand": {
        "vt": 0x29E6C80, "execute": 0xE56830, "type_id": 0x380E, "factory": 0xE53C00,
        "reason": "not army; leave alone",
    },
    "CPauseGame": {
        "vt": 0x29E6D38, "execute": 0xE54FF0, "type_id": 0x29EC, "factory": 0xE53990,
        "size": 0x50, "isvalid": 0x188D90, "isvalid_kind": "TRUE",
        "reason": "pause/unpause — speed-adjacent; IsValid always TRUE",
    },
}

DRAIN_EDGES = {
    "during_exec_drop": "session+0x6CC && !session+0x726",
    "gate_725": 0x725,
    "executing_flag": 0x6CC,
    "defer_flag_726": 0x726,
    "tick": 0x84,
    "sticky_postexec_wrapper": 0xF8,
    "empty_ring_drain_advances": True,
    "recreate": 0x22D8AD0,
}


def summarize() -> dict:
    return {
        "posting": "DISABLED",
        "pipeline": PIPELINE,
        "post_gates": POST_GATES,
        "factory_table": FACTORY_TABLE,
        "isvalid_paths": ISVALID_PATHS,
        "drain_edges": DRAIN_EDGES,
        "never_post": {
            k: {
                "vt": hex(v["vt"]),
                "type_id": hex(v["type_id"]) if "type_id" in v else None,
                "reason": v["reason"],
            }
            for k, v in NEVER_POST.items()
        },
        "remaining_army_orders": {
            k: {"vt": hex(v["vt"]), "type_id": hex(v["type_id"]), "factory": hex(v["factory"])}
            for k, v in REMAINING_ARMY_ORDERS.items()
        },
        "base": BASE,
        "move": MOVE,
        "strategic": STRATEGIC,
        "cancel": CANCEL,
        "startgame": STARTGAME,
        "chat": CHAT,
        "orders": {
            k: {
                "vt": hex(v["vt"]),
                "type_id": hex(v["type_id"]),
                "size": hex(v["size"]),
                "factory": hex(v["factory"]) if "factory" in v else None,
                "serialize": hex(v["serialize"]) if "serialize" in v else None,
                "deserialize": hex(v["deserialize"]) if "deserialize" in v else None,
            }
            for k, v in ORDERS.items()
        },
        "army_move_subjects": ARMY_MOVE_SUBJECTS,
    }
