# -*- coding: utf-8 -*-
import json, hashlib, sys
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import re

# complete theatergroup clip through ret
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
mp=json.loads(Path("research/t163_script_token_map.json").read_text(encoding="utf-8"))
id2name={i["token"]:i["name"] for i in mp}
cs=Cs(CS_ARCH_X86, CS_MODE_64)
raw=pe.read_rva(0x16d9e10, 0x16d9ea6-0x16d9e10) or b""
lines=[]
for i in cs.disasm(raw, 0x16d9e10):
    a=f"0x{i.address:x}  {i.mnemonic} {i.op_str}"
    m=re.search(r"(edx|r8d|r9d|esi|edi|eax|ecx), 0x([0-9a-f]+)", i.op_str)
    if m:
        tok=int(m.group(2),16)
        if tok in id2name:
            a += "  ; TOKEN "+id2name[tok]
    lines.append(a)
Path("research/_t184_clip_theatergroup_writer_0x16d9e10.txt").write_text("\n".join(lines)+"\n", encoding="utf-8")

ROOT=Path(".")
INV=Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
sha=hashlib.sha256(INV.read_bytes()).hexdigest()
assert sha=="ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254", sha

(ROOT/"research/t184_inventory_sha256.json").write_text(json.dumps({
    "path":str(INV),"sha256":sha,"updated":False,
    "reason":"ABI only; empty orders/FM/theater groups and empty GS_COMBATS not promoted; theatre unit list is not formation.army_id",
    "counts":{"fields":116,"tables":14,"columns":3,"verified":43,"unverified":73},
}, indent=2)+"\n", encoding="utf-8")

handle={
    "id_writer":"0x22858a0",
    "layout":"handle type at this+0x8, id at this+0xc; tokens id 0xb and type 0xe1",
    "subhandle_writer":"0x22857c0",
    "subhandle_layout":"r8 points at the handle: type=dword[r8], id=dword[r8+4]. Used as this+8 for groups, this+0x18 for CArmy",
    "clip":"research/_t184_clip_base_id_writer_0x22858a0.txt"
}

formation={
    "game":"HOI4 1.19.5.0.7c6c","pid":26976,"read_only":True,
    "handle":handle,
    "CTheatre":{
        "writer":"0xf81510","vtable":"0x29f22b8",
        "id":"0x22858a0 → type +0x8, id +0xc",
        "arrays":{
            "area":{"token":"0x2b95","data":"+0x18","size":"+0x24","elem":"CControllerArea*; province id at [elem+0x28]+0xa4; omit if size<=0"},
            "front":{"token":"0x29e0","data":"+0x50","size":"+0x5c","omit_if_size_le_0":True},
            "unit":{"token":"0x28a3","data":"+0x68","size":"+0x74","elem":"CArmy*; handle at +0x18 written via 0x22857c0; omit if size<=0"},
            "orders_group":{"token":"0x30ae","data":"+0x80","size":"+0x8c","elem":"COrdersGroup*; 0x25458c0 virtual serialize; omit if size<=0"},
            "field_marshal_group":{"token":"0x3801","data":"+0x98","size":"+0xa4","elem":"CArmyGroup*; omit if size<=0"},
            "theater_group":{"token":"0x35d1","data":"+0xc8","size":"+0xd4","elem":"CTheaterGroup*; omit if size<=0"}
        },
        "clip":"research/_t184_clip_theatre_writer_0xf81510.txt"
    },
    "COrdersGroup":{
        "writer":"0xc4d030","schema_role":"world.armies (集团军)",
        "id":"type +0x8, id +0xc via 0x22858a0",
        "name":"+0x160 (written iff [+0x170]!=0)",
        "members":{"data":"+0x50","size":"+0x5c","unit_handle_via_vcall_plus_0x18":True,"token_unit":"0x28a3"},
        "leader":{"ptr":"+0x88","handle_at":"+8","token":"0x28b7","written_iff_nonzero":True},
        "leader_unit":{"ptr":"+0x68"},
        "order_instance":{"source_array":"+0x98 / size +0xa4","token":"0x35f7"},
        "field_marshal_group_flag":{"byte":"+0x39","token":"0x3801","note":"boolean flag, not the parent pointer"},
        "clip":"research/_t184_clip_ordersgroup_writer_0xc4d030.txt"
    },
    "CArmyGroup":{
        "writer":"0xc4cfa0","schema_role":"world.army_groups (集团军群); derived, jmp 0xc4d030",
        "child_orders_groups":{"token":"0x30ae","data":"+0x230","size":"+0x23c","handle_at_child+8":True,"via":"0x22857c0"},
        "collapse":{"byte":"+0x248","token":"0x3a2e","written_iff_nonzero":True},
        "clip":"research/_t184_clip_armygroup_writer_0xc4cfa0.txt"
    },
    "CTheaterGroup":{
        "writer":"0x16d9e10",
        "id":"0x22858a0",
        "priority":"+0x20","name":"+0x28",
        "orders_group":{"data":"+0x48","size":"+0x54","handle_at_child+8":True},
        "clip":"research/_t184_clip_theatergroup_writer_0x16d9e10.txt"
    },
    "live_eth":{
        "theatres":1,"theatre_id":43,"handle_type":67,
        "unit_array_size":21,"unit_ids":list(range(1829,1850)),
        "orders_group":0,"field_marshal_group":0,"theater_group":0,
        "area_size":1,"front_size":6,
        "note":"21 own CArmy are theatre members; this is not formation.army_id. Groups empty. front size 6 is a structure candidate only, not promoted as plans."
    },
    "promoted":False,
    "why":"official empty group arrays omit keys (distinguishable encoding) but this scene has no army/army-group object, so army_id / army_group_id / world.armies / world.army_groups cannot be proven. Theatre unit list is not the formation contract."
}
(ROOT/"research/t184_formation_writers.json").write_text(json.dumps(formation, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

combat={
    "CLandCombat":{
        "serialize_vtable":"0x2a23898 slot 0x10 → 0x134d5e0 jmp 0x147fe80",
        "writer":"0x147fe80",
        "id":"0x22858a0 type +0x8 id +0xc",
        "location":"CProvince* at +0x28, id at +0xa4, token 0x286d",
        "day":"+0x30","duration":"+0x34",
        "attacker":{"ptr":"+0x18","token":"0x28f5","via":"0x25458c0 virtual serialize, typically CLandCombatant"},
        "defender":{"ptr":"+0x20","token":"0x28f6"},
        "terrain":"from [+0x38]+0x18 if byte [+0x38]+0x10",
        "clip":"research/_t184_clip_landcombat_writer_0x147fe80.txt"
    },
    "CLandCombatant":{
        "writer":"0x134d5f0",
        "front":{"token":"0x29e0","data":"+0xe8","size":"+0xf4","unit_handle_at_elem+0x18":True,"omit_if_size_le_0":True},
        "reserves":{"token":"0x29e2","data":"+0x100","size":"+0x10c","unit_handle_at_elem+0x18":True},
        "retreat":{"token":"0x2920","data":"+0x118","size":"+0x124","unit_handle_at_elem+0x18":True},
        "clip":"research/_t184_clip_landcombatant_writer_0x134d5f0.txt"
    },
    "no_carmy_current_combat_pointer_bound":True,
    "gs_combats":{"location":"GS+0x268","size":0},
    "promoted":False,
    "why":"official combat/combatant membership ABI is bound, but GS+0x268 is empty and no CArmy IsInCombat / current CLandCombat* reader is bound; cannot write in_combat=false"
}
(ROOT/"research/t184_combat_writers.json").write_text(json.dumps(combat, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

cmd={
    "commandlist_plus8":"still official type dword at command+8 written via 0x2546ce0 (t183)",
    "scan":"no mov dword [reg+8], OrderType-or-command-token immediates found in .text",
    "note":"objects that use 0x22858a0 also store handle type at +8; without a live command object we cannot map +8 onto schema OrderType",
    "promoted":False
}
(ROOT/"research/t184_command_plus8.json").write_text(json.dumps(cmd, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

supply={
    "named_tokens_this_batch":["out_of_supply_days 0x335f (already t182)","out_of_supply_factor 0x312e is a modifier, not unit in_supply"],
    "no_in_supply_or_isolated_token_on_CArmy":True,
    "ratio_still_72":True,
    "promoted":False
}
(ROOT/"research/t184_supply_named_tokens.json").write_text(json.dumps(supply, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

offp=ROOT/"calling/tables/offsets_input_windows_1.19.5.json"
off=json.loads(offp.read_text(encoding="utf-8"))
off["formation_combat_writers_t184"]={
    "handle":"type +0x8 id +0xc (0x22858a0); CArmy unit handle at +0x18 (0x22857c0)",
    "CTheatre_writer":"0xf81510",
    "CTheatre_unit":"+0x68 data +0x74 size; live ETH size 21, ids 1829-1849; not formation.army_id",
    "COrdersGroup_writer":"0xc4d030 (world.armies)",
    "CArmyGroup_writer":"0xc4cfa0 then jmp 0xc4d030; child orders_groups at +0x230/+0x23c",
    "CTheaterGroup_writer":"0x16d9e10; child orders_groups at +0x48/+0x54",
    "CLandCombat_writer":"0x147fe80; location [+0x28]+0xa4; attacker +0x18; defender +0x20",
    "CLandCombatant":"front +0xe8/+0xf4, reserves +0x100/+0x10c, retreat +0x118/+0x124; unit handle +0x18",
    "promoted":False,
    "proofs":[
        "research/t184_formation_writers.json",
        "research/t184_combat_writers.json",
        "research/t184_live_theatre.json"
    ]
}
offp.write_text(json.dumps(off, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("proofs ok", sha)
