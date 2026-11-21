# -*- coding: utf-8 -*-
import json, hashlib, re
from pathlib import Path

ROOT = Path(".")
INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
sha = hashlib.sha256(INV.read_bytes()).hexdigest()
assert sha == "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254", sha
(ROOT / "research/t182_inventory_sha256.json").write_text(json.dumps({
    "path": str(INV),
    "sha256": sha,
    "updated": False,
    "reason": "no field promoted; empty official arrays/flags do not prove order.type=idle or in_combat=false",
    "counts": {"fields": 116, "tables": 14, "columns": 3, "verified": 43, "unverified": 73},
}, indent=2) + "\n", encoding="utf-8")

writers = {
  "game": "HOI4 1.19.5.0.7c6c",
  "pid": 26976,
  "read_only": True,
  "secondary_interface": {
    "location": "CArmy+0x10",
    "vtable_rva": "0x29d6f78",
    "writer": "0xced2e0",
    "note": "rcx is already CArmy+0x10; writer offsets add 0x10 to get CArmy absolute slots"
  },
  "base_writer": "0xc5c0a0",
  "path_serializer": {
    "rva": "0x1d2bf0",
    "header": "pdx i32 array: data = [r8], size = dword [r8+0xc]",
    "empty_skip": "test ebx, ebx; jle 0x1d2c7f — size<=0 omits the key",
    "clip": "research/_t182_clip_path_serializer_0x1d2bf0.txt" if Path("research/_t182_clip_path_serializer_0x1d2bf0.txt").exists() else "inlined in checkpoint; see 0x1d2bf0"
  },
  "fields": {
    "path": {"token": "0x174", "name": "path", "writer_off": "0x1f0", "ca_off": "0x200", "size_ca": "0x20c", "empty_omits_key": True},
    "full_path": {"token": "0x362c", "name": "full_path", "writer_off": "0x210", "ca_off": "0x220", "size_ca": "0x22c", "empty_omits_key": True},
    "commandlist": {"token": "0xcb", "name": "commandlist", "writer_off": "0x2b0", "ca_off": "0x2c0", "size_ca": "0x2cc", "stride": 8, "element_token_at": "+8", "empty_omits_key": True},
    "location": {"token": "0x286d", "name": "location", "writer_off": "0x1e0", "ca_off": "0x1f0", "note": "CProvince*; id at +0xa4; already verified as current province"},
    "previous": {"token": "0x29a3", "name": "previous", "writer_off": "0x1e8", "ca_off": "0x1f8"},
    "support_attack": {"token": "0x2eda", "name": "support_attack", "writer_off": "0x1d8", "ca_off": "0x1e8"},
    "last_combat_date": {"token": "0x2fdf", "name": "last_combat_date", "gate_writer": "0x1b8", "gate_ca": "0x1c8", "date_ca": "0x1d0", "note": "historical date; not current in_combat"},
    "movement_progress": {"token": "0x28a4", "name": "movement_progress", "writer_off": "0x230", "ca_off": "0x240"},
    "move_priority": {"token": "0x37bc", "name": "move_priority", "writer_off": "0x238", "ca_off": "0x248", "default_skipped": 1},
    "retreat": {"token": "0x2920", "name": "retreat", "writer_off": "0x23c", "ca_off": "0x24c", "type": "byte", "written_iff_nonzero": True},
    "withdraw": {"token": "0x38ec", "name": "withdraw", "writer_off": "0x23d", "ca_off": "0x24d", "type": "byte", "written_iff_nonzero": True},
    "strategic_redeployment": {"token": "0x2edb", "name": "strategic_redeployment", "writer_off": "0x29f", "ca_off": "0x2af", "type": "byte", "written_iff_nonzero": True},
    "out_of_supply_days": {"token": "0x335f", "name": "out_of_supply_days", "writer_off": "0x488", "ca_off": "0x498", "written_iff_positive": True},
    "execute_order": {"writer_off": "0x48c", "ca_off": "0x49c"},
    "was_paradropped": {"writer_off": "0x498", "ca_off": "0x4a8"},
    "max_supply": {"token": "0x3a43", "name": "max_supply", "writer_off": "0x5f0", "ca_off": "0x600", "live_fixed_div_100000": 108.0},
    "supply_gain": {"token": "0x4cec", "name": "supply_gain", "writer_off": "0x5f8", "ca_off": "0x608", "live_fixed_div_100000": 0.0},
    "army_current_supply_ratio": {"token": "0x4ced", "name": "army_current_supply_ratio", "writer_off": "0x600", "ca_off": "0x610", "live_fixed_div_100000": 72.0, "not_a_0_to_1_ratio": True}
  },
  "not_unit_fields": {
    "GetOrderType": {
      "funcs": ["0x10b2c60", "0x10b0380"],
      "object": "COrderInstance-like +0x30",
      "values": {"1": "ORDER_MOVE", "3": "ORDER_INVASION", "4": "likely PARADROP"},
      "note": "battle-plan types, not world.own_units.order.type"
    },
    "land_combat_id": {
      "token": "0x34a6",
      "written_at": "0x2091bc",
      "slot": "[obj+0x748] in 0x208f90",
      "sibling": "navy_id 0x34a5 at +0x74c",
      "note": "not a CArmy field; do not use as unit combat id"
    }
  },
  "promoted": False
}
(ROOT / "research/t182_carmy_writers.json").write_text(json.dumps(writers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

empty = {
  "rule": "official empty list or zero flag may prove a structure candidate and an official encoding, but must not be promoted as order.type=idle or in_combat=false",
  "session": {"pid": 26976, "own_units": 21, "hour_tick": 60759371},
  "live": {
    "commandlist": {"ca": "CArmy+0x2c0 data, +0x2cc size", "size": 0, "units": 21, "writer_omits_key": True},
    "path": {"ca": "CArmy+0x200 data, +0x20c size", "size": 0, "units": 21, "writer_omits_key": True},
    "full_path": {"ca": "CArmy+0x220 data, +0x22c size", "size": 0, "units": 21, "writer_omits_key": True},
    "support_attack": {"ca": "CArmy+0x1e8", "ptr": "0x0", "units": 21},
    "previous": {"ca": "CArmy+0x1f8", "ptr": "0x0", "units": 21},
    "retreat": {"ca": "CArmy+0x24c", "value": 0, "units": 21, "written_iff_nonzero": True},
    "withdraw": {"ca": "CArmy+0x24d", "value": 0, "units": 21},
    "strategic_redeployment": {"ca": "CArmy+0x2af", "value": 0, "units": 21},
    "movement_progress": {"ca": "CArmy+0x240", "value": 0, "units": 21},
    "out_of_supply_days": {"ca": "CArmy+0x498", "value": 0, "units": 21, "writer_skips_if_le_0": True},
    "gs_combats": {"location": "GS+0x268", "data": 0, "size": 0},
    "supply_ratio_610": 72.0,
    "max_supply_600": 108.0
  },
  "why_not_promoted": {
    "in_combat": "no official CArmy IsInCombat / current CLandCombat* reader bound; last_combat_date is historical; empty GS+0x268 is a structure candidate only",
    "order": "commandlist / path / full_path official-empty and retreat/withdraw/SR official-zero do not equal schema enum idle; GetOrderType is a plan-object type at +0x30, not unit.order.type. Do not write empty arrays as false/idle.",
    "supply.ratio": "official token army_current_supply_ratio at CA+0x610 is 72.0 under /100000, same rejection as t165 (not a 0..1 ratio). Do not invent 72/108.",
    "in_supply_isolated": "no named isolated / in_supply token on CArmy; oos_days==0 is an official skip, not the boolean contract",
    "formation": "not rebound this batch; t165 theatres exist with empty groups — structure only",
    "leaders.assigned_to": "is_assigned token 0x385b writers 0x26940 / 0x14a8ec0 not yet bound to this field"
  },
  "promoted": False
}
(ROOT / "research/t182_empty_not_idle.json").write_text(json.dumps(empty, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# offsets key
offp = ROOT / "calling/tables/offsets_input_windows_1.19.5.json"
off = json.loads(offp.read_text(encoding="utf-8"))
off["combat_order_supply_t182"] = {
    "secondary_interface": "CArmy+0x10",
    "writers": ["0xced2e0", "0xc5c0a0"],
    "path_serializer": "0x1d2bf0",
    "commandlist": "CArmy+0x2c0 data, +0x2cc size, stride 8; token 0xcb omitted when size==0",
    "path": "CArmy+0x200 data, +0x20c size; token 0x174",
    "full_path": "CArmy+0x220 data, +0x22c size; token 0x362c",
    "location": "CArmy+0x1f0 CProvince* (writer +0x1e0)",
    "retreat": "CArmy+0x24c byte, written iff nonzero",
    "withdraw": "CArmy+0x24d",
    "strategic_redeployment": "CArmy+0x2af",
    "out_of_supply_days": "CArmy+0x498, skipped if <=0",
    "max_supply": "token 0x3a43 at CArmy+0x600",
    "army_current_supply_ratio": "token 0x4ced at CArmy+0x610; live 72.0 /100000, not a 0..1 ratio",
    "supply_gain": "token 0x4cec at CArmy+0x608",
    "not": "GetOrderType +0x30 is COrderInstance (ORDER_MOVE/INVASION); land_combat_id 0x34a6 is [obj+0x748] in 0x208f90, not CArmy",
    "promoted": False,
    "proofs": [
      "research/t182_carmy_writers.json",
      "research/t182_empty_not_idle.json",
      "research/t182_carmy_order_supply_live.json"
    ]
}
offp.write_text(json.dumps(off, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("offsets inserted, D sha", sha)
