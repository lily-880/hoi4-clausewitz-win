from pathlib import Path
import json, re

# ---- freeze t192 live SHA ----
p=Path("research/test_t192_input_army_leader.py")
t=p.read_text(encoding="utf-8")
old='''        rec = json.loads((ROOT / "research/t192_inventory_sha256.json").read_text(encoding="utf-8"))
        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, T192_SHA)
        self.assertEqual(rec["sha256"], T192_SHA)
'''
new='''        rec = json.loads((ROOT / "research/t192_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["sha256"], T192_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t192's recorded hash
'''
if old not in t: raise SystemExit("t192 sha block missing")
t=t.replace(old,new)
# relax live unverified asserts for fields this batch promotes
old='''        self.assertIn("| world.own_units.formation.army_group_id | 未验证 |", text)
        self.assertIn("| world.armies.plan_id | 未验证 |", text)
        self.assertIn("| world.army_groups.army_group_id | 未验证 |", text)
'''
new='''        # formation.army_group_id / army_groups.* / armies.plan_id stayed unverified in t192; later batches may promote them
        self.assertIn("| world.own_units.order.type | 未验证 |", text)
'''
# The t192 file may have slightly different lines - show them if missing
if old not in t:
    print("t192 unverified block not exact, context:")
    for i,l in enumerate(t.splitlines(),1):
        if "army_group" in l or "plan_id" in l or "未验证" in l:
            print(f"{i}:{l}")
else:
    t=t.replace(old,new)
    print("relaxed t192 unverified live asserts")
p.write_text(t, encoding="utf-8")
print("patched test_t192")

# ---- freeze t188 plan_id live assert ----
p=Path("research/test_t188_input_plans.py")
t=p.read_text(encoding="utf-8")
old='''        self.assertIn("| world.plans.plan_id | 未验证 |", text)
        self.assertIn("| world.plans.type | 未验证 |", text)
'''
new='''        self.assertIn("| world.plans.type | 未验证 |", text)
        # world.plans.plan_id stayed unverified in t188; later batches may promote it
'''
if old not in t:
    print("t188 block not exact")
    for i,l in enumerate(t.splitlines(),1):
        if "world.plans" in l:
            print(f"{i}:{l}")
    raise SystemExit("t188")
p.write_text(t.replace(old,new), encoding="utf-8")
print("patched test_t188")

# ---- offsets.py ----
p=Path("calling/offsets.py")
t=p.read_text(encoding="utf-8")
old='''    "OG_MEMBER_THISADJ": 0xB8,  # live this-adjust from member interface pointer back to CArmy
'''
new='''    "OG_MEMBER_THISADJ": 0xB8,  # live this-adjust from member interface pointer back to CArmy
    "OG_PARENT_ARMY_GROUP": 0x1B8,  # CArmyGroup*; t193 army 1 after CArmyGroupCommand. Inverse of CArmyGroup+0x230.
    "AG_CHILD_ORDERS": 0x230,  # official CArmyGroup writer 0xc4cfa0 child COrdersGroup* array / size +0x23c
    "OI_TYPE": 0x30,  # COrderInstance type dword; token 0xe1. t193 NewRoot writes 2; 1=ORDER_MOVE, 3=ORDER_INVASION still the only named GetOrderType values
    "OI_PATH": 0x70,  # official path array, token 0x174; still empty after this NewRoot (provinces landed at +0x258)
    "OI_STATES": 0xE0,  # token 0x2e3b
    "OI_INSTANCE_ID": 0x244,  # token 0x30af
    "OI_CAN_EXECUTE": 0x248,  # byte, token 0x30b2 iff nonzero; not plans.executing
'''
if old not in t: raise SystemExit("offsets OG_MEMBER missing")
p.write_text(t.replace(old,new), encoding="utf-8")
print("patched offsets.py")

# ---- input_loaded_fields assigned_to + new readers ----
p=Path("calling/input_loaded_fields.py")
t=p.read_text(encoding="utf-8")
old='''        typ = r.i(lp + 0x1048)
        aid = r.i(lp + 0x104C)
        if typ or aid:
            if typ != 53:
                raise ObservationError('unknown assigned_to handle type')
            item['assigned_to'] = {'kind': 'army', 'id': aid}
        result.append(item)
'''
new='''        typ = r.i(lp + 0x1048)
        aid = r.i(lp + 0x104C)
        if typ or aid:
            item['assigned_to'] = assigned_to_from_handle(r, country, typ, aid)
        result.append(item)
'''
if old not in t: raise SystemExit("assigned_to block missing")
t=t.replace(old,new)

# insert helpers after HANDLE_TYPE_ORDERS_GROUP constants / own_armies
# Add assigned_to_from_handle, own_army_groups, unit_formation_army_group_id, own_plans
# and extend own_armies with plan_id.

old='''            item['unit_ids'] = unit_ids
            armies.append(item)
    return armies, ev
'''
new='''            item['unit_ids'] = unit_ids
            insts = r.array(gp + 0x98, 256)
            if insts:
                # singular plan_id: official hang-off; one live instance in t193
                r.require(insts[0], 'COrderInstance')
                item['plan_id'] = r.i(insts[0] + 0x244)
            armies.append(item)
    return armies, ev
'''
if old not in t: raise SystemExit("own_armies tail missing")
t=t.replace(old,new)

insert='''
def assigned_to_from_handle(r, country, typ, iid):
    """Map CArmyLeader+0x1048 handle to {kind,id}. Type 53 is shared by army and army_group; resolve RTTI."""
    if typ != HANDLE_TYPE_ORDERS_GROUP:
        raise ObservationError('unknown assigned_to handle type')
    for tp in r.array(country + 0x168, 64):
        r.require(tp, 'CTheatre')
        for gp in r.array(tp + 0x80, 256):
            if r.i(gp + 8) == typ and r.i(gp + 0xc) == iid:
                name = r.class_name(gp) if hasattr(r, 'class_name') else None
                # LoadedReader stores class_name as callable
                cls = r.class_name(gp)
                if cls == '.?AVCOrdersGroup@@':
                    return {'kind': 'army', 'id': iid}
                if cls == '.?AVCArmyGroup@@':
                    return {'kind': 'army_group', 'id': iid}
                raise ObservationError('assigned_to type 53 resolved to unexpected class')
        for gp in r.array(tp + 0x98, 256):
            if r.i(gp + 8) == typ and r.i(gp + 0xc) == iid:
                r.require(gp, 'CArmyGroup')
                return {'kind': 'army_group', 'id': iid}
    raise ObservationError('assigned_to handle did not resolve')


def own_army_groups(r, country):
    """world.army_groups from CTheatre+0x98 CArmyGroup*; official writer 0xc4cfa0 then jmp 0xc4d030."""
    groups = []
    ev = {'theatre_count': 0, 'army_group_count': 0}
    for tp in r.array(country + 0x168, 64):
        r.require(tp, 'CTheatre')
        ev['theatre_count'] += 1
        for gp in r.array(tp + 0x98, 256):
            r.require(gp, 'CArmyGroup')
            ev['army_group_count'] += 1
            typ = r.i(gp + 8)
            gid = r.i(gp + 0xc)
            if typ != HANDLE_TYPE_ORDERS_GROUP:
                raise ObservationError('unexpected CArmyGroup handle type')
            item = {'army_group_id': gid}
            name = r.string(gp + 0x160)
            if name:
                item['name'] = name
            leader = r.q(gp + 0x88)
            if leader:
                r.require(leader, 'CArmyLeader')
                item['leader_id'] = r.i(leader + 0xc)
            army_ids = []
            for child in r.array(gp + 0x230, 256):
                r.require(child, 'COrdersGroup')
                if r.i(child + 8) != HANDLE_TYPE_ORDERS_GROUP:
                    raise ObservationError('unexpected child orders_group handle type')
                aid = r.i(child + 0xc)
                back = r.q(child + 0x1b8)
                if back != gp:
                    raise ObservationError('army-group child backlink mismatch')
                army_ids.append(aid)
            item['army_ids'] = army_ids
            groups.append(item)
    return groups, ev


def unit_formation_army_group_id(r, army):
    """formation.army_group_id via CArmy+0xC0 orders group then COrdersGroup+0x1B8 CArmyGroup*."""
    gp = r.q(army + 0xc0)
    if not gp:
        return None, {'present': False}
    r.require(gp, 'COrdersGroup')
    parent = r.q(gp + 0x1b8)
    if not parent:
        return None, {'present': False, 'army_id': r.i(gp + 0xc)}
    r.require(parent, 'CArmyGroup')
    typ = r.i(parent + 8)
    gid = r.i(parent + 0xc)
    if typ != HANDLE_TYPE_ORDERS_GROUP:
        raise ObservationError('formation.army_group_id is not a CArmyGroup handle')
    return gid, {'present': True, 'group': hex(parent), 'army_id': r.i(gp + 0xc)}


def own_plans(r, country):
    """world.plans from COrdersGroup+0x98 COrderInstance*; official writer 0x10d1450."""
    plans = []
    ev = {'instance_count': 0}
    for tp in r.array(country + 0x168, 64):
        r.require(tp, 'CTheatre')
        for gp in r.array(tp + 0x80, 256):
            r.require(gp, 'COrdersGroup')
            army_id = r.i(gp + 0xc)
            for ip in r.array(gp + 0x98, 256):
                r.require(ip, 'COrderInstance')
                ev['instance_count'] += 1
                item = {
                    'plan_id': r.i(ip + 0x244),
                    'assigned_army_ids': [army_id],
                }
                # type / path / executing intentionally not emitted: type 2 is not yet a named GetOrderType; official path +0x70 may be empty; can_execute is not executing
                plans.append(item)
    return plans, ev


'''
# insert after unit_formation_army_id function
anchor='''    return aid, {'present': True, 'group': hex(gp)}


'''
if anchor not in t: raise SystemExit("unit_formation_army_id tail missing")
t=t.replace(anchor, anchor+insert, 1)
p.write_text(t, encoding="utf-8")
print("patched input_loaded_fields.py")

# syntax check
import ast
ast.parse(Path("calling/input_loaded_fields.py").read_text(encoding="utf-8"))
ast.parse(Path("calling/offsets.py").read_text(encoding="utf-8"))
print("syntax ok")
