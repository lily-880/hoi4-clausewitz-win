"""Offset tables for Windows hoi4.exe.

IMPORTANT: Upstream Clausewitz-MCP offsets were recovered against Linux ELF 1.19.2.
They are NOT valid for Windows PE 1.19.4 unless re-verified.

Load order for WINDOWS_GLOBALS:
  1. built-in stubs (None)
  2. calling/offsets_verified.json  (committed only after manual verification)
  3. calling/offsets_runtime.json   (local live-gs heuristic; gitignored)

Static RTTI/vtable RVAs that are safely proven live under ASLR (COL slot MATCH)
are in PROVEN_STATIC and calling/tables/offsets_windows_1.19.4.json.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

TARGET = {
    "os": "Windows",
    "exe": "hoi4.exe",
    "game_version": "1.19.4.x",
    "version_name": "Operation Postern",
    "upstream_ref": "https://github.com/smerss/Clausewitz-MCP (Linux 1.19.2 ELF)",
    "exe_sha256_1_19_4": "CF781ED178CD801643B233B7E3FCD1C0EFD19BD01AECD24BF07A35F69F10476F",
}

HYPOTHESIS_STRUCT = {
    "PDXARRAY_DATA": 0x0,
    "PDXARRAY_CAP": 0x8,
    "PDXARRAY_SIZE": 0xC,
    "PDXARRAY_ALLOC": 0x10,
    "PDXARRAY_SZ": 0x18,
    "FIXED": 100000,
    "DAYS_PER_YEAR": 365,
    "GS_COMBATS": 0x268,
    "GS_COUNTRIES": 0x310,
    "GS_MAJORS": 0x328,
    "GS_TAG2INDEX": 0x340,
    "GS_PLAYER_TAG": 0x518,
    "GS_STRATEGIC_AIR_MANAGER": 0x690,  # CStrategicAirManager* (live RTTI)
    "GS_CHARACTER_MANAGER": 0x6A8,  # CCharacterManager* (live RTTI)
    "GS_PAUSE_HOURS": 0x908,  # Linux; NOT verified on Windows (garbage)
    "GS_DATE_YEAR": 0x478,  # hypothesis: i32 year (seen 1936)
    "GS_DATE_AUX": 0x47C,  # hypothesis: i32 (seen 31); maybe day-of-year — not full date
    # Country (CCountry) — verified in-game via -hands_off (Haiti 1936), two samples
    "CO_ARMIES": 0x290,  # CPdxArray<CArmy*>; sizes seen 17 then 50; Windows CArmy == division-level
    "CO_DIV_TEMPLATES": 0x1B8,  # CPdxArray<CReferencedDivisionTemplate*> (live)
    "CO_FLEETS": 0x278,  # CPdxArray<CFleet*> (live Haiti)
    "CO_THEATRES": 0x168,  # CPdxArray<CTheatre*> (live HAI+majors)
    "CO_STATES": 0x460,  # CPdxArray<CState*> (live HAI+majors; twin@0x478 same size peacetime)
    "CO_CONTROLLER_AREAS": 0x548,  # CPdxArray<CControllerArea*> (live HAI=9)
    "CO_OWNER_AREAS": 0x560,  # CPdxArray<COwnerArea*> (live HAI=9)
    "CO_MODIFIERS": 0x5D0,  # CPdxArray<CModifier*> (live HAI=36)
    # CArmy fields (division-like on Windows 1.19.4 — all 17/17 paused HAI)
    "CA_SUBUNIT_DEF": 0x138,  # CSubUnitDefinition*
    "CA_PROVINCE": 0x1F0,  # CProvince*
    "CA_DIV_TEMPLATE": 0x3B8,  # CReferencedDivisionTemplate*
    # CStrategicAirManager (via GS_STRATEGIC_AIR_MANAGER)
    "SAM_STRATEGIC_AIRS": 0x30,  # CPdxArray<CStrategicAir*> (live world=440)
    "SAM_AIR_BASES": 0x90,  # CPdxArray<CAirBase*> (live world=1082)
    "SAM_AIR_BASES_FILTERED": 0xD8,  # CPdxArray<CAirBase*> (live=14; role TBD)
    # CCharacterManager (via GS_CHARACTER_MANAGER)
    "CM_CHARACTERS": 0x10,  # CPdxArray<CCharacter*> (live world=9661)
    "CM_CHARACTERS_ACTIVE": 0x28,  # CPdxArray<CCharacter*> (live=2361; role TBD)
    # CTheatre fields (primary theatre from CO_THEATRES)
    "TH_FRONTS": 0x50,  # CPdxArray<CFront*> (live HAI=6, major0=10)
    "TH_ARMIES": 0x68,  # CPdxArray<CArmy*> (live HAI=17 matches CO_ARMIES)
}

# Safely static-proven (RTTI + live COL verification). NOT globals / NOT Post.
PROVEN_STATIC = {
    "CGameState_vtable": 0x279F0F0,
    "CGameState_vtable_secondary": 0x279F148,
    "CCurrentGameState_vtable": 0x279F168,
    "CCurrentGameState_vtable_secondary": 0x279F1C0,
    "CInGameIdler_vtable": 0x29E5838,
    "CFrontEndIdler_vtable": 0x29C6D30,
    "CGameIdler_vtable": 0x27B4158,
    "CGameApplication_vtable": 0x2796308,
    "CCommand_vtable": 0x279F4A0,
    "CArmy_vtable": 0x29D6D68,
    "CArmy_vtable_mi": [0x29D6F48, 0x29D6FB8, 0x29D7000],
    "CArmyGroup_vtable": 0x29CEE28,
    "CArmyGroup_vtable_mi": [0x29CEEA0],
    "CUnit_vtable": 0x29CFAC0,
    "CInGameIdler_queue_field_hyp": 0x530,  # idler vt+0x90/+0x78/+0x80/+0x88 load [this+0x530]; LIVE=CGameApplication — NOT queue (2m vt scan confirms)
    "CInGameIdler_vt_post_wrapper": 0xE34E90,
    "CFrontEndIdler_vt_forward": 0xB8DCA0,  # same [this+0x530]->jmp[rax+0x90] shape
    "CGameApplication_vt90_setter": 0x1B14F0,  # NOT Post -- swaps this+0x380 (CSession*)
    "CGameApplication_vt88_session_getter": 0x17F880,  # mov rax,[rcx+0x380]; ret — CSession*
    "CGameApplication_SESSION": 0x380,  # CSession* (live RTTI)
    "CSession_SERVER": 0x40,  # CServer* (live CDummyServer in SP)
    "CInGameIdler_vt88_session_forward": 0xB8E390,  # [this+0x530]->App.vt+0x88
    "FN_CMD_QUEUE_POST": 0x22C41E0,  # CSession post/drop gate (AI + UI); SP sink CDummyServer vt+0x28
    "FN_CMD_QUEUE_POST_SINK_DUMMY": 0x23F5CD0,  # proven enqueue into listener+0xa0 ring
    "FN_CMD_QUEUE_DRAIN_DUMMY": 0x23F64E0,  # CDummyServer vt+0x30: ring->list clone
    "FN_CMD_QUEUE_CLEAR_DUMMY": 0x23F5AD0,  # CDummyServer vt+0x48: clear list+ring
    "CDummyServer_RING": 0xA0,  # concurrent ring (lock/buf/cap/idx)
    "CDummyServer_PENDING": 0x58,  # linked list head after drain
    "G_SESSION": 0x34FFBE8,  # Phase 2ay live == App+0x380 CSession*
    "G_COMMAND_QUEUE": 0x34FFBE8,  # alias of G_SESSION
    "G_POST_LISTENERS": 0x3667BE8,  # ptr to CServer* array fan-out
    "G_POST_LISTENER_COUNT": 0x3667BF4,
    # Phase 2r — Execute tick (READ-ONLY; posting still DISABLED)
    "FN_SESSION_UPDATE": 0x22C6410,  # CSession tick; state==2 drains+stages+Execute
    "FN_EXECUTE_LOOP": 0x22C4710,  # second list Execute loop (server.vt+0x78 -> +0x40)
    "FN_CMD_ISVALID_WRAP": 0x22D8EA0,  # calls cmd.vt+0x48 IsValid
    "CCommand_VT_ISVALID": 0x48,  # NOT Execute (2q mislabel corrected in 2r)
    "CCommand_VT_EXECUTE": 0x50,  # real Execute slot
    "CCommand_VT_POSTEXEC": 0x58,  # post-Execute hook
    "CDummyServer_EXECLIST": 0x40,  # list head via vt+0x78 getter 0x247620
    "FN_CMD_QUEUE_POST_SINK_NETWORK": 0x23FA830,  # CNetworkServer vt+0x28 (MP; not live SP)
    "FN_CMD_QUEUE_DRAIN_NETWORK": 0x23FB470,  # CNetworkServer vt+0x30 — also fills +0x58 only
    "CSession_EXECUTING_FLAG": 0x6CC,  # set around Execute; Post-during-exec DROPS
    "CSession_EXEC_COUNTER": 0x6C8,
    "CSession_DRAIN_COUNTER": 0x60,
    # Phase 2t — move command / session staging / post-exec list
    "CMoveCommand_VT": 0x2A2C790,
    "CMoveCommand_SIZE": 0x88,  # factory 0x13fb000 (2w corrects 2t 0x58 mislabel)
    "CMoveCommand_FACTORY": 0x13FB000,
    "CChatCommand_VT": 0x2A27F28,
    "CChatCommand_SIZE": 0x98,
    "CChatCommand_EXECUTE": 0x13CAEE0,
    "COrderExecuteCommand_VT": 0x2A85468,
    "COrderExecuteCommand_EXECUTE": 0x18D6430,
    "CCommand_VT_EARLY_0x60": 0x60,  # Post early gate; Move stubs to false
    "CCommand_VT_EARLY_0x80": 0x80,
    "CStartGameCommand_VT": 0x2A5F448,
    "CStartGameCommand_SIZE": 0x28,
    "CStartGameCommand_EXECUTE": 0x16DE180,
    "CCommand_STUB_TRUE": 0x188D90,  # mov al,1;ret — StartGame early/post-exec
    "CCommand_STUB_FALSE": 0x11D530,  # xor al,al;ret — Move early-drop
    # Phase 2aa — speed cmds documented RO only; NEVER Post (5x ban)
    "CIncreaseGameSpeedCommand_VT": 0x29F37C8,
    "CDecreaseGameSpeedCommand_VT": 0x29F3880,
    "CSetGameSpeedCommand_VT": 0x29F3938,
    "CHourlyTickCommand_VT": 0x29F3710,
    "SESSION_EARLY_BYPASS_0x725": 0x725,
    "SESSION_POST_DURING_EXEC_0x726": 0x726,
    "SESSION_TICK_0x84": 0x84,
    "CDummyServer_VT": 0x2BCB040,
    "CDummyServer_POST_0x28": 0x23F5CD0,
    "CDummyServer_DRAIN_0x30": 0x23F64E0,
    "CDummyServer_DRAIN_STORE_0x58_SITE": 0x23F6629,  # mov [rbx+0x58], rdx
    "CDummyServer_EXECLIST_0x78": 0x247620,  # lea rax,[rcx+0x40];ret
    "CNetworkServer_VT": 0x2BCB330,
    "CNetworkServer_POST_0x28": 0x23FA830,
    "CNetworkServer_INSERT": 0x23FA510,
    "SERVER_EXECLIST_HEAD_0x40": 0x40,
    "SERVER_DRAINLIST_HEAD_0x58": 0x58,
    "SERVER_SEQ_0xD0": 0xD0,
    "SESSION_SKIP_AUTH_0x3C": 0x3C,
    "SERVER_PENDING_LIST_0x58": 0x58,
    "SERVER_RING_LOCK_0xA0": 0xA0,
    "SERVER_RING_DATA_0xB0": 0xB0,
    "SERVER_RING_COUNT_0xC8": 0xC8,
    "SERVER_VT_PENDING_0x40": 0x40,  # lea [rcx+0x58]
    "SERVER_VT_EXECLIST_0x78": 0x78,  # lea [rcx+0x40]
    "FN_RING_RECREATE": 0x22D8AD0,
    "CCommand_VT_CLONE_0x68": 0x68,
    "SESSION_STATE2_EXECUTE_SITE": 0x22C6C9D,
    "CMoveCommand_TYPEID": 0x28A2,
    "CCancelMovementCommand_TYPEID": 0x28AF,
    "CChatCommand_TYPEID": 0x184,
    "CStartGameCommand_TYPEID": 0x359E,
    "CCommand_VT_WRITE_0x10": 0x10,
    "CCommand_VT_READ_0x20": 0x20,
    "CCommand_WRITE_SHARED": 0x22D9390,
    "CCommand_READ_SHARED": 0x22D90F0,
    "CCommand_VT_PAYLOAD_WRITE_0xA0": 0xA0,
    "CCommand_VT_PAYLOAD_READ_0xA8": 0xA8,
    "CMoveCommand_VT_0xA8_THUNK": 0x1403570,
    "CUnitMoveAction_DESERIALIZE": 0x12C3340,  # vt+0xb8
    "CUnitMoveAction_APPLY": 0xC4F450,  # 2am corrects 2ak 0x12af450 (abs/base miscalc); wrapper
    "CUnitMoveAction_APPLY_INNER": 0xC4D700,  # real body; unit mode switch + path apply
    "FN_TOKEN_WRITE": 0x2546BA0,  # serialize tag writer
    "FN_TOKEN_TO_STRING": 0x253EB90,  # token id -> SSO name in G_TOKEN_ARRAY
    "FN_TOKEN_NAME_GET": 0x1F8360,  # (writer, token) -> std::string*
    "G_TOKEN_ARRAY": 0x368F5A0,  # ptr; entry size 32 (MSVC SSO string)
    "G_TOKEN_MAX": 0x368F574,  # i32
    # Phase 2an — CUnitMoveAction field offs (serialize-proven)
    "CUnitMoveAction_UNIT_HANDLE": 0x10,
    "CUnitMoveAction_PROVINCE_ARR": 0x18,
    "CUnitMoveAction_PROVINCE_SIZE": 0x24,
    "CUnitMoveAction_PATH_ARR": 0x30,
    "CUnitMoveAction_PATH_SIZE": 0x3C,
    "CUnitMoveAction_CLEAR": 0x50,
    "CUnitMoveAction_SAFE": 0x51,
    "CUnitMoveAction_SAFE_UNTIL_END": 0x52,
    "CUnitMoveAction_SAFE_NONSAFE_FB": 0x53,
    "CUnitMoveAction_AVOID": 0x55,
    "CUnitMoveAction_MOVE_PRIORITY": 0x58,
    "CUnitMoveAction_STICKY": 0x5C,
    "CMoveCommand_ACTION_EMBED": 0x28,
    # Phase 2ao
    "FN_MOVE_PRIORITY_ENUM": 0x19D7560,
    "MOVE_PRIORITY_FRONT_ORDER": 0,
    "MOVE_PRIORITY_NORMAL": 1,
    "MOVE_PRIORITY_PLAYER_ORDER": 2,
    "MOVE_PRIORITY_AI_PLAYER_ORDER": 3,
    "CCancelMovement_UNITS_DATA": 0x28,
    "CCancelMovement_UNITS_COUNT": 0x34,
    "CCancelMovement_STICKY": 0x40,
    "FN_HANDLE_RESOLVE": 0x6E4800,
    "CCancelMovementCommand_SERIALIZE": 0x1404130,
    "CChatCommand_SERIALIZE": 0x13D7FA0,
    "CMoveCommand_EXECUTE": 0x13FC990,  # thunk -> CUnitMoveAction.vt+0x48
    "CUnitMoveAction_VT": 0x2A1F648,
    "CUnitMoveAction_EXECUTE": 0x12C2670,  # real move body
    "CUnitMoveAction_ISVALID": 0x12C2CA0,
    "CUnitMoveAction_CTOR": 0x12C1770,
    "CUnitMoveAction_SERIALIZE": 0x12C3920,  # vt+0xc0
    "CMoveCommand_VT_0xA0_THUNK": 0x1404590,
    "FN_TYPEID_FACTORY_LOOKUP": 0x22D8D20,
    "TYPEID_FACTORY_TABLE": 0x35011E0,
    "CCancelMovementCommand_FACTORY": 0x13FACE0,
    "CChatCommand_FACTORY": 0x13CA430,
    "CStartGameCommand_FACTORY": 0x16DD5A0,
    "CStartGameCommand_CLONE": 0x16DD0D0,  # vt+0x68 — sticky postexec
    "CMoveCommand_CLONE": 0x13F9350,
    "SESSION_UPDATE_DRAIN_CALLS": "0x22c6521/0x22c6543/0x22c664b vt+0x30",
    "CSession_STAGE_ARRAY": 0x48,
    "CSession_STAGE_COUNT": 0x54,
    "CSession_POSTEXEC_HEAD": 0xF8,
    "CSession_POSTEXEC_TAIL": 0x100,
    "CSession_POSTEXEC_COUNT": 0x108,
    # Phase 2u — +0x40 execlist filler
    "CCommand_FLAG_EXECLIST": 0x1A,  # nonzero → NetworkServer posts to +0x40 not +0x58
    "NETWORK_POST_EXECLIST_INSERT": 0x23FA510,  # branch site; +0x40 path at 0x23fa578
    "CDummyServer_EXECLIST_HEAD": 0x40,
    "CDummyServer_EXECLIST_TAIL": 0x48,
    "CDummyServer_EXECLIST_COUNT": 0x50,
    # Phase 2v — Post gates / CancelMovement
    "CCancelMovement_VT": 0x2A2C9B8,
    "CCancelMovement_EXECUTE": 0x13FBBD0,
    "CCancelMovement_ISVALID": 0x13FED40,
    "CSession_POST_FLAG_725": 0x725,
    "CSession_POST_FLAG_726": 0x726,
    "CSession_POST_FLAG_3C": 0x3C,
    "CServer_VT_SINK_POST": 0x28,  # FN_CMD_QUEUE_POST delivery
    "RTTI_CGameState_name": 0x31E75A0,
    "RTTI_CCurrentGameState_name": 0x31E78B8,
    "RTTI_CCommand_name": 0x31E74B8,
    "CGameState_ctor_lea": 0x1D78AE,
}

WINDOWS_GLOBALS = {
    "G_GAMESTATE": None,
    "G_IDLER": None,
    "G_COUNTRYTAG_DB": None,
    "G_CONSOLE_MANAGER": None,
    "G_DEFAULT_ALLOC": None,
    "FN_CONSOLE_EXECUTE": None,
}

RUNTIME = {
    "image_base": None,
    "image_size": None,
    "pid": None,
}


def _load_json(path: str) -> None:
    if not os.path.isfile(path):
        return
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return
    for k, v in data.items():
        if k in WINDOWS_GLOBALS and isinstance(v, int):
            WINDOWS_GLOBALS[k] = v


_load_json(os.path.join(HERE, "offsets_verified.json"))
_load_json(os.path.join(HERE, "offsets_runtime.json"))


def require(name: str) -> int:
    v = WINDOWS_GLOBALS.get(name)
    if v is None:
        raise RuntimeError(
            "Offset %s is not recovered for Windows %s yet. "
            "See research/WINDOWS_OFFSETS.md" % (name, TARGET["game_version"])
        )
    return v
