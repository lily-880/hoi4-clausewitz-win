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
    "CMoveCommand_EXECUTE": 0x13FC990,  # thunk -> CUnitMoveAction.vt+0x48
    "CUnitMoveAction_VT": 0x2A1F648,
    "CUnitMoveAction_EXECUTE": 0x12C2670,  # real move body
    "CUnitMoveAction_ISVALID": 0x12C2CA0,
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
