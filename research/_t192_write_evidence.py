import json
from pathlib import Path

ev = {
    "authorized_by": ["pt180u"],
    "pid": 26976,
    "tag": "ETH",
    "date": "1936-01-01 12:00",
    "hour_tick": 60759371,
    "paused": True,
    "speed_index": 0,
    "commands": [
        {
            "name": "COrderGroupCommand",
            "factory_idx": 2983,
            "factory_rva": "0x18d0140",
            "subjects": {"theatre": [67, 43], "units": [[51, 1838]]},
            "dry_isvalid": 1,
            "post_rax": 1,
            "result": "created COrdersGroup id=1 name=第1集团军 members=[1838] leader=null",
        },
        {
            "name": "CSetArmyLeaderCommand",
            "factory_idx": 3369,
            "factory_rva": "0x18d0c10",
            "subjects": {"leader": [4713, 312], "orders_group": [53, 1], "deploy_hq": 0},
            "dry_isvalid": 1,
            "post_rax": 1,
            "result": "COrdersGroup+0x88 -> leader 312; CArmyLeader+0x1048={53,1}; deployed+0x1068 still 0",
        },
    ],
    "keep_unit_1829_path": [8036],
    "promoted": [
        "world.own_units.formation.army_id",
        "world.armies.army_id",
        "world.armies.name",
        "world.armies.leader_id",
        "world.armies.unit_ids",
        "world.leaders.assigned_to",
    ],
    "not_promoted": {
        "world.own_units.formation.army_group_id": "no CArmyGroup created",
        "world.army_groups.*": "CTheatre+0x98 and army-group arrays still empty",
        "world.armies.plan_id": "COrdersGroup order_instance +0x98 size 0",
        "CArmyLeader.deployed": "stayed 0; not assigned_to",
        "assigned_to army_group/unit kinds": "only type 53 / kind=army observed",
    },
}
Path("research/t192_army_leader.json").write_text(json.dumps(ev, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("wrote evidence json")

# add live_fields to proofs in offsets json
jp = Path("calling/tables/offsets_input_windows_1.19.5.json")
off = json.loads(jp.read_text(encoding="utf-8"))
proofs = off["army_leader_t192"]["proofs"]
if "research/t192_live_fields.json" not in proofs:
    proofs.append("research/t192_live_fields.json")
    jp.write_text(json.dumps(off, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("proofs", off["army_leader_t192"]["proofs"])
