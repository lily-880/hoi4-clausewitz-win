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
    "gettypeid": 0x13FE350,
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
    "factory_idx": 4505,
    "execute": 0x13FC990,  # shared thunk
    "clone": 0x13F9C10,
    "serialize": 0x1404590,  # thunk -> action.vt+0xc0 (shared w/ Move)
    "deserialize": 0x1403570,  # thunk -> action.vt+0xb8 (shared w/ Move)
    "isvalid": 0x1402260,
    "gettypeid": 0x13FE420,
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
    "clone": 0x13F8DB0,
    "isvalid": 0x13FED40,
    "gettypeid": 0x13FE2D0,
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
    "factory": 0x16DD5A0,
    "size": 0x28,
    "clone": 0x16DD0D0,
    "serialize": 0x154030,
    "deserialize": 0xD4EE30,
    "execute": 0x16DE180,
    "isvalid": 0x188D90,  # TRUE stub
    "gettypeid": 0x16DE500,
    "sticky_session_off": 0xF8,  # wrapper; +0 -> cmd*
    "note": "Live sticky post-exec sample on paused SP (Phase 2bl); factory/serdes filled 2bp",
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
        "isvalid": 0x18def40,
        "isvalid_kind": "FN",
        "fields": {"order_index": 0x30, "execute_order": 0x34, "all": 0x35},
    },
    "COrderAssignCommand": {
        "factory": 0x18cfca0,
        "vt": 0x2A84498, "type_id": 0x303E, "size": 0x50,
        "clone": 0x18CD5B0, "serialize": 0x18E80F0, "deserialize": 0x18E1A70, "execute": 0x18D41B0,
        "isvalid": 0x18de900,
        "isvalid_kind": "FN",
        "fields": {"units_data": 0x28, "units_count": 0x34, "order_index": 0x48, "assign_to_minimum_order": 0x4C},
    },
    "COrderUnassignCommand": {
        "factory": 0x18d09b0,
        "vt": 0x2A84550, "type_id": 0x304D, "size": 0x50,
        "clone": 0x18CEBB0, "serialize": 0x18E91B0, "deserialize": 0x18E2EE0, "execute": 0x18DB050,
        "isvalid": 0x18e01d0,
        "isvalid_kind": "FN",
        "fields": {"units_data": 0x28, "units_count": 0x34, "unassign_group": 0x48, "unassign_army_group_instances": 0x49},
    },
    "COrderDeleteCommand": {
        "factory": 0x18cffa0,
        "vt": 0x2A843E0, "type_id": 0x303F, "size": 0x38,
        "clone": 0x18CDA90, "serialize": 0x18E86E0, "deserialize": 0x18E1FE0, "execute": 0x18D5FE0,
        "isvalid": 0x18deee0,
        "isvalid_kind": "FN",
        "fields": {"order_index": 0x30},
    },
    "COrderNewFrontCommand": {
        "factory": 0x18d0340,
        "vt": 0x2A84B10, "type_id": 0x3327, "size": 0x70,
        "clone": 0x18CE0E0, "serialize": 0x18E8AF0, "deserialize": 0x18E25C0, "execute": 0x18D9000,
        "isvalid": 0x18df4e0,
        "isvalid_kind": "FN",
        "fields": {
            "sub_group": 0x30, "units_data": 0x38, "units_count": 0x44,
            "path": 0x50, "attach": 0x68, "split_from": 0x6C, "blitz": 0x6D, "withdraw": 0x6E,
        },
    },
    "COrderNewRootCommand": {
        "factory": 0x18d03d0,
        "vt": 0x2A84DF0, "type_id": 0x3328, "size": 0x70,
        "clone": 0x18CE200, "serialize": 0x18E8BF0, "deserialize": 0x18E26D0, "execute": 0x18D99C0,
        "isvalid": 0x18df570,
        "isvalid_kind": "FN",
    },
    "COrderNewFallbackCommand": {
        "factory": 0x18d02c0,
        "vt": 0x2A84C80, "type_id": 0x33D7, "size": 0x60,
        "clone": 0x18CDFF0, "serialize": 0x18E8A60, "deserialize": 0x18E2500, "execute": 0x18D8FC0,
        "isvalid": 0x18df4b0,
        "isvalid_kind": "FN",
    },
    "COrderGroupCommand": {
        "factory": 0x18d00d0,
        "vt": 0x2A83D68, "type_id": 0x2ECF, "size": 0x60,
        "clone": 0x18CDC70, "serialize": 0x18E8830, "deserialize": 0x18E21D0, "execute": 0x18D64F0,
        "isvalid": 0x18defe0,
        "isvalid_kind": "FN",
        "fields": {"theatre": 0x48, "theater_group": 0x50, "army_group": 0x58},
    },
    "CArmyGroupCommand": {
        "factory": 0x18cf710,
        "vt": 0x2A83ED8, "type_id": 0x3861, "size": 0x80,
        "clone": 0x18CCCC0, "serialize": 0x18E7A50, "deserialize": 0x18E0E60, "execute": 0x18D25D0,
        "isvalid": 0x18ddf70,
        "isvalid_kind": "FN",
    },
    "CSetArmyLeaderCommand": {
        "factory": 0x18d0ba0,
        "vt": 0x2A85520, "type_id": 0x3051, "size": 0x40,
        "clone": 0x18CEF00, "serialize": 0x18E9390, "deserialize": 0x18E3210, "execute": 0x18DB2C0,
        "isvalid": 0x18e04d0,
        "isvalid_kind": "FN",
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
    # EXTRA land/naval IsValid (RO 2br)
    "CMoveArmiesInTheaterCommand": {
        "rva": 0x18DE7E0,
        "kind": "FN",
        "notes": "Vector count@+0x34; walks handles@+0x28 via resolve; empty→fail",
    },
    "CMoveArmyGroupInTheaterCommand": {
        "rva": 0x18DE8A0,
        "kind": "FN",
        "notes": "Thunk: rcx+=0x28; call helper 0x10f12f0 (group handle valid?)",
    },
    "CCancelRunningAwayCommand": {
        "rva": 0x13EED30,
        "kind": "FN",
        "notes": "Thunk rcx+=0x28 → unit-vector helper; empty count@+0x34 fails",
    },
    "CRailwayGunManualOrderCommand": {
        "rva": 0xF01F50,
        "kind": "FN",
        "notes": "Feature/session gates + subject@+0x28/+0x40",
    },
    "CSetQuickDeployPreferenceCommand": {
        "rva": 0x19D43A0,
        "kind": "FN",
        "notes": "Preference tag@+0x40 count; walks handles@+0x28 count@+0x34",
    },
    "CSetCountryGarrisonPriorityCommand": {
        "rva": 0x11F26A0,
        "kind": "FN",
        "notes": "country@+0x28 >0 AND priority@+0x2c <=2 → TRUE else FALSE (tight)",
    },
    "CNavalMoveCommand": {
        "rva": 0x13EE960,
        "kind": "FN",
        "notes": "Fleet/ship count@+0x40 must be >0; feature gates",
    },
    "CMoveShipsCommand": {
        "rva": 0x1400300,
        "kind": "FN",
        "notes": "Ship counts@+0x40/+0x44; resolve helper 0xc57080; complex multi-gate",
    },
    # ORDERS IsValid (RO 2br)
    "COrderAssignCommand": {
        "rva": 0x18DE900,
        "kind": "FN",
        "notes": "Header/subject checks @+0x10/+0x18; count@+0x34",
    },
    "COrderUnassignCommand": {
        "rva": 0x18E01D0,
        "kind": "FN",
        "notes": "Subject cluster@+0x40",
    },
    "COrderDeleteCommand": {
        "rva": 0x18DEEE0,
        "kind": "FN",
        "notes": "Order id pair@+0x28/+0x2c/+0x30",
    },
    "COrderNewFrontCommand": {
        "rva": 0x18DF4E0,
        "kind": "FN",
        "notes": "Front geometry @+0x28..+0x30 + flags@+0x5c/+0x68",
    },
    "COrderNewRootCommand": {
        "rva": 0x18DF570,
        "kind": "FN",
        "notes": "Root handles@+0x48/+0x4c",
    },
    "COrderNewFallbackCommand": {
        "rva": 0x18DF4B0,
        "kind": "FN",
        "notes": "Fallback field@+0x54",
    },
    "COrderGroupCommand": {
        "rva": 0x18DEFE0,
        "kind": "FN",
        "notes": "Group/subject @+0x10/+0x18/+0x30/+0x3c/+0x50",
    },
    "CArmyGroupCommand": {
        "rva": 0x18DDF70,
        "kind": "FN",
        "notes": "Army-group ids @+0x10/+0x18/+0x3c/+0x48/+0x50",
    },
    "CSetArmyLeaderCommand": {
        "rva": 0x18E04D0,
        "kind": "FN",
        "notes": "Leader/army handles @+0x10/+0x18/+0x28..+0x34",
    },
}

# Remaining army/order-adjacent subtypes (RTTI+factory RO stubs; not full serialize proof)
# type_id = preferred biased form when dual-encoded
REMAINING_ARMY_ORDERS = {
    "CMassMoveCommand": {
        "type_id": 0x341F, "factory": 0x13FAEC0, "vt": 0x2A2C848, "factory_idx": 4343,
        "size": 0x60, "clone": 0x13F90B0, "serialize": 0x14042F0, "deserialize": 0x1403160,
        "execute": 0x13FC310, "isvalid": 0x13FFBA0, "gettypeid": 0x13FE320,
    },
    "CMassCancelMovementCommand": {
        "type_id": 0x3630, "factory": 0x11D8FD0, "vt": 0x2A0FC40, "factory_idx": 4872,
        "size": 0x40, "clone": 0x11D5B50, "serialize": 0x11FC660, "deserialize": 0x11F7F30,
        "execute": 0x11E1520, "isvalid": 0x11F0A10, "gettypeid": 0x11EAA00,
    },
    "CToggleStrategicDeploymentCommand": {
        "type_id": 0x3CE0, "factory": 0x13FB640, "vt": 0x2A2CA70, "factory_idx": 6584,
        "size": 0x40, "clone": 0x13F9D50, "serialize": 0x1404B40, "deserialize": 0x1403E70,
        "execute": 0x13FDE90, "isvalid": 0x14025C0, "gettypeid": 0x13FE440,
    },
    "COrderSetPathCommand": {
        "type_id": 0x3039, "factory": 0x18D08E0, "vt": 0x2A84778, "factory_idx": 3345,
        "size": 0x58, "clone": 0x18CEA40, "serialize": 0x18E90C0, "deserialize": 0x18E2D60,
        "execute": 0x18DAEF0, "isvalid": 0x18DFF00, "gettypeid": 0x18DCC30,
    },
    "CDeleteOrderGroupCommand": {
        "type_id": 0x304E, "factory": 0x18CF9E0, "vt": 0x2A83E20, "factory_idx": 3366,
        "size": 0x30, "clone": 0x18CD140, "serialize": 0x18E7DF0, "deserialize": 0x18E1490,
        "execute": 0x18D3300, "isvalid": 0x18DE300, "gettypeid": 0x18DCA20,
    },
    "COrderDeleteAllCommand": {
        "type_id": 0x33F1, "factory": 0x18CFED0, "vt": 0x2A84270, "factory_idx": 4297,
        "size": 0x30, "clone": 0x18CD980, "serialize": 0x18E7DF0, "deserialize": 0x18E1490,
        "execute": 0x18D58F0, "isvalid": 0x18DE2F0, "gettypeid": 0x18DCAD0,
    },
    "COrderInsertFrontCommand": {
        "type_id": 0x3398, "factory": 0x18D0150, "vt": 0x2A84A58, "factory_idx": 4208,
        "size": 0x98, "clone": 0x18CDD50, "serialize": 0x18E8910, "deserialize": 0x18E22E0,
        "execute": 0x18D65F0, "isvalid": 0x18DF230, "gettypeid": 0x18DCB30,
    },
    "COrderReshapeCommand": {
        "type_id": 0x339E, "factory": 0x18D06C0, "vt": 0x2A84830, "factory_idx": 4214,
        "size": 0x50, "clone": 0x18CE690, "serialize": 0x18E8E90, "deserialize": 0x18E2A70,
        "execute": 0x18DA7D0, "isvalid": 0x18DF6C0, "gettypeid": 0x18DCBE0,
    },
    "COrderConnectCommand": {
        "type_id": 0x33B1, "factory": 0x18CFE00, "vt": 0x2A849A0, "factory_idx": 4233,
        "size": 0x40, "clone": 0x18CD810, "serialize": 0x18E8560, "deserialize": 0x18E1E30,
        "execute": 0x18D54A0, "isvalid": 0x18DED50, "gettypeid": 0x18DCAB0,
    },
    "COrderReconnectCommand": {
        "type_id": 0x33B0, "factory": 0x18D0470, "vt": 0x2A848E8, "factory_idx": 4232,
        "size": 0x40, "clone": 0x18CE2F0, "serialize": 0x18E8CE0, "deserialize": 0x18E27E0,
        "execute": 0x18D9E10, "isvalid": 0x18DF5B0, "gettypeid": 0x18DCB90,
    },
    "CAutoMergeOrdersCommand": {
        "type_id": 0x3552, "factory": 0x18CF910, "vt": 0x2A84BC8, "factory_idx": 4650,
        "size": 0x38, "clone": 0x18CCFE0, "serialize": 0x18E7D50, "deserialize": 0x18E1390,
        "execute": 0x18D31F0, "isvalid": 0x18DE2C0, "gettypeid": 0x18DCA00,
    },
    "CAssignToArmyGroupCommand": {
        "type_id": 0x3886, "factory": 0x18CF8A0, "vt": 0x2A83F90, "factory_idx": 5470,
        "size": 0x50, "clone": 0x18CCF10, "serialize": 0x18E7C80, "deserialize": 0x18E12A0,
        "execute": 0x18D2E00, "isvalid": 0x18DE250, "gettypeid": 0x18DC9F0,
    },
    "CRemoveFromArmyGroupCommand": {
        "type_id": 0x3887, "factory": 0x18D0A80, "vt": 0x2A84048, "factory_idx": 5471,
        "size": 0x40, "clone": 0x18CED10, "serialize": 0x18E92A0, "deserialize": 0x18E3090,
        "execute": 0x18DB1C0, "isvalid": 0x18E0310, "gettypeid": 0x18DCC70,
    },
    "CDeployArmyHqCommand": {
        "type_id": 0x282B, "factory": 0x13FAE60, "vt": 0x2A2CEC0, "factory_idx": 1283,
        "size": 0x38, "clone": 0x13F9020, "serialize": 0x14042B0, "deserialize": 0x14030A0,
        "execute": 0x13FC190, "isvalid": 0x13FF490, "gettypeid": 0x13FE310,
    },
    "CWithdrawArmyHqCommand": {
        "type_id": 0x2833, "factory": 0x13FB710, "vt": 0x2A2CF78, "factory_idx": 1291,
        "size": 0x30, "clone": 0x13F9EC0, "serialize": 0x1404BC0, "deserialize": 0x1403F10,
        "execute": 0x13FE2A0, "isvalid": 0x14027C0, "gettypeid": 0x13FE460,
    },
}

NEVER_POST = {
    "CIncreaseGameSpeedCommand": {
        "vt": 0x29F37C8, "execute": 0xF85930, "type_id": 0x28D7,
        "size": 0x28, "factory": 0xF84830,
        "reason": "speed/5x ban",
    },
    "CDecreaseGameSpeedCommand": {
        "vt": 0x29F3880, "execute": 0xF853F0, "type_id": 0x28D8,
        "size": 0x48, "factory": 0xF84780,
        "reason": "speed/5x ban",
    },
    "CSetGameSpeedCommand": {
        "vt": 0x29F3938, "execute": 0xF85B50, "type_id": 0x2F42,
        "size": 0x30, "factory": 0xF84880,
        "reason": "speed/5x ban",
    },
    "CHourlyTickCommand": {
        "vt": 0x29F3710, "execute": 0xF85630, "type_id": 0x2F3C,
        "size": 0x28, "factory": 0xF847E0,
        "reason": "hourly/speed ban",
    },
    "CSendPingCommand": {
        "vt": 0x29E6C80, "execute": 0xE56830, "type_id": 0x380E,
        "size": 0x78, "factory": 0xE53C00,
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
    # DummyServer drain 0x23f64e0 (rbx=server) — RO 2br
    "ring_lock_a0": 0xA0,
    "ring_ptr_b8": 0xB8,
    "ring_idx_c0": 0xC0,
    "ring_slot_c8": 0xC8,
    "pending_list_60": 0x60,
    "pending_count_68": 0x68,
    "drain_clones_via_vt68": True,
    "drain_dtor_via_vt0": True,
}

# Session / Post / SessionUpdate edges (RO 2br). Not a Post enable.
SESSION_EDGES = {
    "g_session": 0x34FFBE8,
    "tick": 0x84,
    "seq_or_count_60": 0x60,
    "auth_skip_3c": 0x3C,
    "gate_725": 0x725,
    "executing_6cc": 0x6CC,
    "exec_counter_6c8": 0x6C8,
    "defer_726": 0x726,
    "sticky_wrapper_f8": 0xF8,
    "sticky_wrapper_layout": {
        "cmd_ptr": 0x0,
        "note": "sess+0xF8 is wrapper not raw CCommand; wrapper+0->cmd; StartGame durable while paused (2br)",
    },
    "post_prologue_0x22c41e0": {
        "early_drop_if": "r8b==0 AND session+0x725==0 AND vt+0x80==0 AND vt+0x60==0",
        "success_path": [
            "cmd+0xc = session.tick(+0x84)",
            "cmd+0x18 word from session+0x60-derived",
            "check session+0x3c / +0x6cc / +0x726",
            "vt+0x80 / auth vt+0x90 paths",
        ],
        "during_exec_drop": "session+0x6CC && !session+0x726",
    },
    "session_update_0x22c6410": {
        "set_6cc_before_execute": True,
        "clear_6cc_after_execute": True,
        "inc_6c8": True,
        "write_sticky_f8": True,
        "execute_site_a": 0x22C6C9D,
    },
}

# Execute path edges (vt+0x50). RO 2br — never call from tooling.
EXECUTE_EDGES = {
    "vt_off": 0x50,
    "wrap_via_session_update": True,
    "site_a": 0x22C6C9D,
    "loop_b": 0x22C4710,
    "note": "Execute only after drain->pending; never call from tooling",
    "kinds_summary": {
        "EXTRA_ARMY": "all FN (land/naval)",
        "ORDERS": "all FN",
        "REMAINING": "all FN",
        "NEVER_POST_Pause": "FN (IsValid TRUE) — ban",
        "STARTGAME": "FN — already executed; sticky residual",
    },
}


# Extra land/theater/niche army-adjacent + sample naval (RO deepen 2bq). Not enable-ready.
EXTRA_ARMY_COMMANDS = {
    "CMoveArmiesInTheaterCommand": {
        "type_id": 0x3a8e,
        "factory": 0x18cfb30,
        "vt": 0x2a84100,
        "size": 0x48,
        "clone": 0x18cd330,
        "serialize": 0x18e7f30,
        "deserialize": 0x18e17c0,
        "isvalid": 0x18de7e0,
        "execute": 0x18d36c0,
        "gettypeid": 0x18dca50,
        "factory_idx": 0x1766,
        "kind": 'land',
        "type_id_kind": 'imm',
        "isvalid_kind": 'FN',
        "fields": {
            "units_vec": 0x28,
            "units_count": 0x34,
            "theater_or_dest": 0x40,
        },
    },
    "CMoveArmyGroupInTheaterCommand": {
        "type_id": 0x3a8f,
        "factory": 0x18cfba0,
        "vt": 0x2a841b8,
        "size": 0x38,
        "clone": 0x18cd400,
        "serialize": 0x18e7fc0,
        "deserialize": 0x18e1890,
        "isvalid": 0x18de8a0,
        "execute": 0x18d3b90,
        "gettypeid": 0x18dca60,
        "factory_idx": 0x1767,
        "kind": 'land',
        "type_id_kind": 'imm',
        "isvalid_kind": 'FN',
        "fields": {
            "group_handle": 0x28,
            "theater_or_dest": 0x30,
        },
    },
    "CCancelRunningAwayCommand": {
        "type_id": 0x3bb4,
        "factory": 0x13fad40,
        "vt": 0x2a2d538,
        "size": 0x30,
        "clone": 0x13f8e80,
        "serialize": 0x14041b0,
        "deserialize": 0x1402e00,
        "isvalid": 0x13eed30,
        "execute": 0x13fbca0,
        "gettypeid": 0x13fe2e0,
        "factory_idx": 0x188c,
        "kind": 'land',
        "type_id_kind": 'imm',
        "isvalid_kind": 'FN',
        "fields": {
            "units_vec": 0x28,
        },
    },
    "CRailwayGunManualOrderCommand": {
        "type_id": 0x4da0,
        "factory": 0xf016f0,
        "vt": 0x29ef160,
        "size": 0x48,
        "clone": 0xf01440,
        "serialize": 0xf02450,
        "deserialize": 0xf022b0,
        "isvalid": 0xf01f50,
        "execute": 0xf01900,
        "gettypeid": 0xf01cb0,
        "factory_idx": 0x2a78,
        "kind": 'land',
        "type_id_kind": 'imm',
        "isvalid_kind": 'FN',
        "fields": {
            "subject": 0x28,
            "extra_30": 0x30,
            "order_or_prov": 0x40,
        },
    },
    "CSetQuickDeployPreferenceCommand": {
        "type_id": 0x3a1c,
        "factory": 0x19cfa50,
        "vt": 0x2a974f0,
        "size": 0x48,
        "clone": 0x19cea50,
        "serialize": 0x19d6d10,
        "deserialize": 0x19d57d0,
        "isvalid": 0x19d43a0,
        "execute": 0x19d1790,
        "gettypeid": 0x19d3390,
        "factory_idx": 0x16f4,
        "kind": 'land',
        "type_id_kind": 'imm',
        "isvalid_kind": 'FN',
        "fields": {
            "handles_vec": 0x28,
            "handles_count": 0x34,
            "pref_tag": 0x40,
            "flag_44": 0x44,
            "word_18": 0x18,
        },
    },
    "CSetCountryGarrisonPriorityCommand": {
        "type_id": 0x4ab4,
        "factory": 0x245f60,
        "vt": 0x27abb08,
        "size": 0x30,
        "clone": 0x2459b0,
        "serialize": 0x11fd060,
        "deserialize": 0x11f94c0,
        "isvalid": 0x11f26a0,
        "execute": 0x11e5980,
        "gettypeid": 0x2490d0,
        "factory_idx": 0x278c,
        "kind": 'land',
        "type_id_kind": 'mem',
        "isvalid_kind": 'FN',
        "fields": {
            "country": 0x28,
            "priority": 0x2c,
        },
    },
    "CNavalMoveCommand": {
        "type_id": 0x3178,
        "factory": 0x13e3be0,
        "vt": 0x2a2a710,
        "size": 0x48,
        "clone": 0x13e1880,
        "serialize": 0x13f3050,
        "deserialize": 0x13f1030,
        "isvalid": 0x13ee960,
        "execute": 0x13e6f00,
        "gettypeid": 0x13ebff0,
        "factory_idx": 0xe50,
        "kind": 'naval_air',
        "type_id_kind": 'imm',
        "isvalid_kind": 'FN',
        "fields": {
            "ships_vec": 0x28,
            "ships_count": 0x34,
            "fleet_count": 0x40,
            "flags_44": 0x44,
        },
    },
    "CMoveShipsCommand": {
        "type_id": 0x3324,
        "factory": 0x13fb060,
        "vt": 0x2a2d258,
        "size": 0x58,
        "clone": 0x13f93f0,
        "serialize": 0x14045a0,
        "deserialize": 0x1403580,
        "isvalid": 0x1400300,
        "execute": 0x13fc9a0,
        "gettypeid": 0x13fe360,
        "factory_idx": 0xffc,
        "kind": 'naval_air',
        "type_id_kind": 'imm',
        "isvalid_kind": 'FN',
        "fields": {
            "ships_vec": 0x28,
            "count_a": 0x40,
            "count_b": 0x44,
            "dest_cluster": 0x48,
        },
    },
}


# Dummy sink serialize → recreate → ring (RO wiring). Live buffer RT still needs midflight/post.
DUMMY_ROUNDTRIP = {
    "sink": 0x23F5CD0,  # CDummyServer.vt+0x28
    "recreate": 0x22D8AD0,
    "factory_lookup": 0x22D8D20,
    "serialize_with_typeid": 0x2545780,  # writes tid then jmp [cmd.vt+0x8]
    "gettypeid_vt_off": 0x58,  # mov dword [rdx], IMM; mov rax,rdx; ret
    "bin_serialize_vt_off": 0x8,  # shared 0x2541580 → call [vt+0x10]
    "bin_serialize_body_vt_off": 0x10,  # shared 0x22D9390
    "bin_deserialize_vt_off": 0x18,  # shared 0x2540FC0; recreate→ba33f0→jmp [vt+0x18]
    "bin_deserialize_body_vt_off": 0x20,  # shared 0x22D90F0
    "token_serialize_vt_off": 0xA0,  # type-specific (Move thunk→action+0xC0)
    "token_deserialize_vt_off": 0xA8,  # type-specific (Move thunk→action+0xB8)
    "ring_embed_off": 0xA0,
    "seq_off": 0xD0,
    "shared_bin_ser": 0x2541580,
    "shared_bin_des": 0x2540FC0,
    "shared_bin_ser_body": 0x22D9390,
    "shared_bin_des_body": 0x22D90F0,
    "note": (
        "RO wiring proven 2bp: GetTypeId→ser_helper→vt+8→recreate(factory+vt+18)→ring. "
        "2bq: sticky StartGame structural ser↔des (token 0x1F3 header inverse) + recreate/factory proven RO; in-process ring embed still STUBBED (needs midflight sample or Post)."
    ),
}


def summarize() -> dict:
    return {
        "posting": "DISABLED",
        "pipeline": PIPELINE,
        "post_gates": POST_GATES,
        "factory_table": FACTORY_TABLE,
        "isvalid_paths": ISVALID_PATHS,
        "dummy_roundtrip": DUMMY_ROUNDTRIP,
        "extra_army_commands": EXTRA_ARMY_COMMANDS,
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
