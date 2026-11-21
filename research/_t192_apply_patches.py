from pathlib import Path
import json, re

ROOT = Path(".")

# ---- test_t191 freeze live SHA ----
p = ROOT/"research/test_t191_input_move_path.py"
t = p.read_text(encoding="utf-8")
old = '''        rec = json.loads((ROOT / "research/t191_inventory_sha256.json").read_text(encoding="utf-8"))
        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, T191_SHA)
        self.assertEqual(rec["sha256"], T191_SHA)
        self.assertTrue(rec["updated"])
'''
new = '''        rec = json.loads((ROOT / "research/t191_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["sha256"], T191_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t191's recorded hash
        self.assertTrue(rec["updated"])
'''
if old not in t:
    raise SystemExit("t191 inventory block not found")
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched test_t191")

# ---- test_t183 freeze promoted-later fields ----
p = ROOT/"research/test_t183_input_assigned_combat_command.py"
t = p.read_text(encoding="utf-8")
old = '''        text = INV.read_text(encoding="utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
        self.assertIn("| world.leaders.assigned_to | 未验证 |", text)
        self.assertIn("| world.own_units.formation.army_id | 未验证 |", text)
'''
new = '''        text = INV.read_text(encoding="utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
        # assigned_to / formation.army_id stayed unverified in t183; later batches may promote them
'''
if old not in t:
    raise SystemExit("t183 inventory block not found")
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched test_t183")

# ---- test_t184 freeze ----
p = ROOT/"research/test_t184_input_formation_combat.py"
t = p.read_text(encoding="utf-8")
old = '''        text = INV.read_text(encoding="utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.formation.army_id | 未验证 |", text)
        self.assertIn("| world.armies.army_id | 未验证 |", text)
        self.assertIn("| world.combats.combat_id | 未验证 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
'''
new = '''        text = INV.read_text(encoding="utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.combats.combat_id | 未验证 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
        # formation.army_id / world.armies.army_id stayed unverified in t184; later batches may promote them
'''
if old not in t:
    raise SystemExit("t184 inventory block not found")
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched test_t184")

# ---- army_subjects recipe ----
p = ROOT/"calling/army_subjects.py"
t = p.read_text(encoding="utf-8")
old = '''def set_army_leader_recipe(leader_handle: list[int] | tuple[int, int],
                           deploy_army_hq: int = 0) -> dict[str, Any]:
    """CSetArmyLeaderCommand — RO only."""
    return {
        "leader_off": 0x28,
        "leader": list(leader_handle),
        "deploy_army_hq_off": 0x38,
        "deploy_army_hq": deploy_army_hq,
        "posting": "DISABLED",
    }
'''
new = '''def set_army_leader_recipe(leader_handle: list[int] | tuple[int, int],
                           orders_group_handle: list[int] | tuple[int, int],
                           deploy_army_hq: int = 0) -> dict[str, Any]:
    """CSetArmyLeaderCommand — RO packing only.

    IsValid/Execute require the orders_group/army handle at +0x30 (t192 live).
    """
    return {
        "leader_off": 0x28,
        "leader": list(leader_handle),
        "orders_group_off": 0x30,
        "orders_group": list(orders_group_handle),
        "deploy_army_hq_off": 0x38,
        "deploy_army_hq": deploy_army_hq,
        "posting": "DISABLED",
    }
'''
if old not in t:
    raise SystemExit("set_army_leader_recipe not found")
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched army_subjects recipe")

# ---- offsets.py ----
p = ROOT/"calling/offsets.py"
t = p.read_text(encoding="utf-8")
old = '''    "CA_OBJECT_SIZE": 0x690,  # live allocation stride between CArmy objects
'''
new = '''    "CA_OBJECT_SIZE": 0x690,  # live allocation stride between CArmy objects
    "CA_ORDERS_GROUP": 0xC0,  # COrdersGroup*; t192 unit 1838 after COrderGroupCommand. Do not read +0x750 (overlaps next 0x690 object).
    "CAL_ASSIGNED_HANDLE": 0x1048,  # CArmyLeader {u32 type, u32 id}; type 53 = COrdersGroup/army. Not deployed +0x1068 (stayed 0 after appoint).
    "OG_MEMBERS": 0x50,  # CPdxArray of member pointers; official writer 0xc4d030 calls vt+0x20 then handle at +0x18
    "OG_LEADER": 0x88,  # CArmyLeader*; official token 0x28b7 handle at leader+8; omit if null
    "OG_NAME": 0x160,  # MSVC string; t192 default "第1集团军"
    "OG_HANDLE_TYPE": 53,  # live COrdersGroup handle type
    "OG_MEMBER_THISADJ": 0xB8,  # live this-adjust from member interface pointer back to CArmy
'''
if old not in t:
    raise SystemExit("CA_OBJECT_SIZE not found")
p.write_text(t.replace(old, new), encoding="utf-8")
print("patched offsets.py")

# ---- input_loaded_fields.py ----
p = ROOT/"calling/input_loaded_fields.py"
t = p.read_text(encoding="utf-8")
old = '''        # assigned_to omitted: self pointer at +0xf10 is NOT assignment evidence.
        result.append(item)
'''
new = '''        # assigned_to is the handle at +0x1048, not deployed +0x1068 and not +0xf10.
        typ = r.i(lp + 0x1048)
        aid = r.i(lp + 0x104C)
        if typ or aid:
            if typ != 53:
                raise ObservationError('unknown assigned_to handle type')
            item['assigned_to'] = {'kind': 'army', 'id': aid}
        result.append(item)
'''
if old not in t:
    raise SystemExit("assigned_to comment not found")
t = t.replace(old, new)

old = '''def unit_movement_path(r, army):
    """Official CArmy+0x200 u32 path; empty is not idle. Promoted t191 after a live Move."""
'''
# insert new functions after unit_movement_path. Find the function end.
# read the function
idx = t.find(old)
if idx < 0:
    raise SystemExit("unit_movement_path not found")
# find next def after this one
next_def = t.find("\ndef ", idx + 10)
body = t[idx:next_def]
print("unit_movement_path body:\n", body)
insert = '''
HANDLE_TYPE_ORDERS_GROUP = 53
ORDERS_GROUP_MEMBER_THISADJ = 0xB8


def own_armies(r, country):
    """world.armies from CTheatre+0x80 COrdersGroup*; official writer 0xc4d030. Promoted t192."""
    armies = []
    ev = {'theatre_count': 0, 'orders_group_count': 0}
    for tp in r.array(country + 0x168, 64):
        r.require(tp, 'CTheatre')
        ev['theatre_count'] += 1
        for gp in r.array(tp + 0x80, 256):
            r.require(gp, 'COrdersGroup')
            ev['orders_group_count'] += 1
            typ = r.i(gp + 8)
            aid = r.i(gp + 0xc)
            if typ != HANDLE_TYPE_ORDERS_GROUP:
                raise ObservationError('unexpected COrdersGroup handle type')
            item = {'army_id': aid}
            name = r.string(gp + 0x160)
            if name:
                item['name'] = name
            leader = r.q(gp + 0x88)
            if leader:
                r.require(leader, 'CArmyLeader')
                item['leader_id'] = r.i(leader + 0xc)
            unit_ids = []
            for mp in r.array(gp + 0x50, 256):
                # official writer: call vt+0x20 then handle at +0x18; live this-adjust is +0xB8
                primary = mp - ORDERS_GROUP_MEMBER_THISADJ
                r.require(primary, 'CArmy')
                uid = r.i(primary + 0x1c)
                if r.q(primary + 0xc0) != gp:
                    raise ObservationError('orders-group member backlink mismatch')
                unit_ids.append(uid)
            item['unit_ids'] = unit_ids
            armies.append(item)
    return armies, ev


def unit_formation_army_id(r, army):
    """formation.army_id from CArmy+0xC0 COrdersGroup*; empty is unaffiliated, not a theatre id."""
    gp = r.q(army + 0xc0)
    if not gp:
        return None, {'present': False}
    r.require(gp, 'COrdersGroup')
    typ = r.i(gp + 8)
    aid = r.i(gp + 0xc)
    if typ != HANDLE_TYPE_ORDERS_GROUP:
        raise ObservationError('formation.army_id is not a COrdersGroup handle')
    return aid, {'present': True, 'group': hex(gp)}


'''
t = t[:next_def] + insert + t[next_def:]
p.write_text(t, encoding="utf-8")
print("patched input_loaded_fields.py")

# ---- offsets_input json ----
jp = ROOT/"calling/tables/offsets_input_windows_1.19.5.json"
off = json.loads(jp.read_text(encoding="utf-8"))
off["army_leader_t192"] = {
    "COrderGroupCommand": {
        "factory_idx": 2983,
        "factory_rva_1_19_5": "0x18d0140",
        "vt": "0x2a84560",
        "isvalid": "0x18df050",
        "execute": "0x18d6560",
        "create_call": "0xc417a0",
        "size": "0x60",
        "pack": "flag +0x28=0; ucrt unit-handle vector +0x30; theatre handle +0x48 (type 67 id 43); +0x50/+0x58 empty",
    },
    "CSetArmyLeaderCommand": {
        "factory_idx": 3369,
        "factory_rva_1_19_5": "0x18d0c10",
        "vt": "0x2a85e20",
        "isvalid": "0x18e0540",
        "execute": "0x18db330",
        "size": "0x40",
        "pack": "leader handle +0x28 (type 4713); orders_group handle +0x30 (type 53); deploy_hq +0x38=0",
    },
    "COrdersGroup_writer": "0xc4d030 still on 1.19.5",
    "COrdersGroup_id": "handle type 53 at +0x8, id at +0xc",
    "COrdersGroup_name": "+0x160",
    "COrdersGroup_members": "+0x50 / +0x5c; vt+0x20 then unit handle at +0x18; live this-adjust 0xB8",
    "COrdersGroup_leader": "+0x88, official token 0x28b7 handle at leader+8; omit if null",
    "CArmy_orders_group": "+0xC0 COrdersGroup*; only the assigned division is non-null; do not use +0x750",
    "CArmyLeader_assigned_handle": "+0x1048 {type,id}; type 53 = army. Not in writer 0xc7e8c0 token list; live contrast plus official group.leader inverse",
    "CArmyLeader_deployed": "+0x1068 token 0x41c7 stayed 0 after a successful appoint; not assigned_to",
    "live": {
        "theatre_type": 67,
        "theatre_id": 43,
        "new_army_id": 1,
        "new_army_name": "第1集团军",
        "member_unit_id": 1838,
        "leader_id": 312,
        "leader_handle_type": 4713,
        "leader_key": "ETH_haile_selassie",
        "paused": True,
        "keep_unit_1829_path": [8036],
    },
    "promoted": [
        "world.own_units.formation.army_id",
        "world.armies.army_id",
        "world.armies.name",
        "world.armies.leader_id",
        "world.armies.unit_ids",
        "world.leaders.assigned_to",
    ],
    "not_promoted": [
        "world.own_units.formation.army_group_id",
        "world.army_groups.army_group_id",
        "world.army_groups.name",
        "world.army_groups.leader_id",
        "world.army_groups.army_ids",
        "world.armies.plan_id",
    ],
    "proofs": [
        "research/t192_post.json",
        "research/t192_readback.json",
        "research/t192_contrast.json",
        "research/t192_army_leader.json",
    ],
}
jp.write_text(json.dumps(off, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("patched offsets_input json, keys", len(off))
print("DONE patches")
