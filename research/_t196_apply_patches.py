# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json, shutil, sys
from pathlib import Path

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
INV_D = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
STAGE_DIR = Path(r"C:\Users\Lenovo\agent-tools")
STAGE = STAGE_DIR / "态势信息读取能力清单.md"
SRC = STAGE_DIR / "t196_inventory_src.md"

AUTHORIZED = ["pt182u", "pt180u"]


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"missing {label}")
    if text.count(old) != 1:
        raise SystemExit(f"not unique {label}: {text.count(old)}")
    return text.replace(old, new)


def patch_own_plans():
    p = ROOT / "calling" / "input_loaded_fields.py"
    text = p.read_text(encoding="utf-8")
    old = (
        "def own_plans(r, country):\n"
        '    """world.plans from COrdersGroup+0x98 COrderInstance*; official writer 0x10d1450."""\n'
        "    plans = []\n"
        "    ev = {'instance_count': 0}\n"
        "    for tp in r.array(country + 0x168, 64):\n"
        "        r.require(tp, 'CTheatre')\n"
        "        for gp in r.array(tp + 0x80, 256):\n"
        "            r.require(gp, 'COrdersGroup')\n"
        "            army_id = r.i(gp + 0xc)\n"
        "            for ip in r.array(gp + 0x98, 256):\n"
        "                r.require(ip, 'COrderInstance')\n"
        "                ev['instance_count'] += 1\n"
        "                item = {\n"
        "                    'plan_id': r.i(ip + 0x244),\n"
        "                    'assigned_army_ids': [army_id],\n"
        "                }\n"
        "                # type / path / executing intentionally not emitted: type 2 is not yet a named GetOrderType; official path +0x70 may be empty; can_execute is not executing\n"
        "                plans.append(item)\n"
        "    return plans, ev\n"
    )
    new = (
        "def own_plans(r, country):\n"
        '    """world.plans from COrdersGroup+0x98 COrderInstance*; official writer 0x10d1450."""\n'
        "    plans = []\n"
        "    ev = {'instance_count': 0}\n"
        "    for tp in r.array(country + 0x168, 64):\n"
        "        r.require(tp, 'CTheatre')\n"
        "        for gp in r.array(tp + 0x80, 256):\n"
        "            r.require(gp, 'COrdersGroup')\n"
        "            army_id = r.i(gp + 0xc)\n"
        "            for ip in r.array(gp + 0x98, 256):\n"
        "                r.require(ip, 'COrderInstance')\n"
        "                ev['instance_count'] += 1\n"
        "                unit_ids = []\n"
        "                for mp in r.array(ip + 0x210, 256):\n"
        "                    # official writer 0x10d1450 token scheduled_member: vt+0x20 then +0x18; live this-adjust +0xB8\n"
        "                    primary = mp - ORDERS_GROUP_MEMBER_THISADJ\n"
        "                    r.require(primary, 'CArmy')\n"
        "                    unit_ids.append(r.i(primary + 0x1c))\n"
        "                item = {\n"
        "                    'plan_id': r.i(ip + 0x244),\n"
        "                    'assigned_army_ids': [army_id],\n"
        "                    'assigned_unit_ids': unit_ids,\n"
        "                    'executing': bool(r.exact(ip + 0x248, 1)[0]),\n"
        "                }\n"
        "                # type / official path +0x70 still omitted: type 2 unnamed; path empty after NewFront\n"
        "                plans.append(item)\n"
        "    return plans, ev\n"
    )
    text = replace_once(text, old, new, "own_plans")
    p.write_text(text, encoding="utf-8")


def patch_offsets_py():
    p = ROOT / "calling" / "offsets.py"
    text = p.read_text(encoding="utf-8")
    old = '    "OI_PATH": 0x70,  # official path array, token 0x174; still empty after this NewRoot (provinces landed at +0x258)\n'
    new = '    "OI_PATH": 0x70,  # official path array, token 0x174; still empty after t196 NewFront (provinces at +0x258 are not vertex/path)\n'
    text = replace_once(text, old, new, "OI_PATH comment")
    old = (
        '    "OI_STATES": 0xE0,  # token 0x2e3b\n'
        '    "OI_INSTANCE_ID": 0x244,  # token 0x30af\n'
        '    "OI_CAN_EXECUTE": 0x248,  # byte, token 0x30b2 iff nonzero; not plans.executing\n'
    )
    new = (
        '    "OI_STATES": 0xE0,  # token 0x2e3b\n'
        '    "OI_SCHEDULED_MEMBER": 0x210,  # CPdxArray, token 0x30b1 scheduled_member; plans.assigned_unit_ids after COrderAssignCommand\n'
        '    "OI_INSTANCE_ID": 0x244,  # token 0x30af\n'
        '    "OI_CAN_EXECUTE": 0x248,  # byte, token 0x30b2 iff nonzero; COrderExecuteCommand writes this; plans.executing promoted t196\n'
    )
    text = replace_once(text, old, new, "OI_CAN_EXECUTE block")
    p.write_text(text, encoding="utf-8")


def patch_offsets_json():
    p = ROOT / "calling" / "tables" / "offsets_input_windows_1.19.5.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    if "plan_execute_assign_t196" in data:
        raise SystemExit("plan_execute_assign_t196 already present")
    data["plan_execute_assign_t196"] = {
        "authorized_by": AUTHORIZED,
        "promoted": [
            "world.plans.assigned_unit_ids",
            "world.plans.executing",
        ],
        "COrderInstance_scheduled_member": "+0x210 token 0x30b1; writer 0x10d1450 vt+0x20 then +0x18; live this-adjust +0xB8; unit 1838 after COrderAssignCommand",
        "COrderInstance_can_execute": "+0x248 token 0x30b2 iff nonzero; COrderExecuteCommand Execute writes this byte; live 0->1 while officially paused",
        "COrderInstance_path": "+0x70 token 0x174 still empty after COrderNewFrontCommand; +0x258/+0x25c not official vertex/path",
        "COrderInstance_type": "+0x30 still 2; GetOrderType still only names 1=ORDER_MOVE and 3=ORDER_INVASION; not promoted",
        "live": {
            "pid": 12948,
            "plan_id": 1,
            "assigned_army_ids": [1],
            "assigned_unit_ids": [1838],
            "executing": True,
        },
    }
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def freeze_test_t193():
    p = ROOT / "research" / "test_t193_input_army_group_plan.py"
    text = p.read_text(encoding="utf-8")
    old = (
        "    def test_inventory_promotes_eight_fields(self):\n"
        '        rec = json.loads((ROOT / "research/t193_inventory_sha256.json").read_text(encoding="utf-8"))\n'
        "        raw = INV.read_bytes()\n"
        "        sha = hashlib.sha256(raw).hexdigest()\n"
        "        self.assertEqual(sha, T193_SHA)\n"
        '        self.assertEqual(rec["sha256"], T193_SHA)\n'
        '        self.assertTrue(rec["updated"])\n'
        '        self.assertEqual(rec["fields"], 116)\n'
        '        self.assertEqual(rec["tables"], 14)\n'
        '        self.assertEqual(rec["columns"], 3)\n'
        '        self.assertEqual(rec["verified"], 62)\n'
        '        self.assertEqual(rec["unverified"], 54)\n'
        '        self.assertFalse(rec["complete_input"])\n'
        '        text = raw.decode("utf-8")\n'
        '        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)\n'
        "        for name in rec[\"promoted\"]:\n"
        '            self.assertIn(f"| {name} | 已验证 |", text)\n'
        '        self.assertIn("| world.plans.type | 未验证 |", text)\n'
        '        self.assertIn("| world.plans.vertex_province_ids | 未验证 |", text)\n'
        '        self.assertIn("| world.plans.executing | 未验证 |", text)\n'
        '        self.assertIn("COrdersGroup+0x1B8", text)\n'
        '        self.assertIn("COrderInstance+0x244", text)\n'
        '        self.assertNotIn("附录", text)\n'
        '        n_tables = sum(1 for ln in text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))\n'
        "        self.assertEqual(n_tables, 14)\n"
    )
    new = (
        "    def test_inventory_promotes_eight_fields(self):\n"
        '        rec = json.loads((ROOT / "research/t193_inventory_sha256.json").read_text(encoding="utf-8"))\n'
        "        # live D SHA may change in later batches; this test pins t193's recorded hash\n"
        '        self.assertEqual(rec["sha256"], T193_SHA)\n'
        '        self.assertTrue(rec["updated"])\n'
        '        self.assertEqual(rec["fields"], 116)\n'
        '        self.assertEqual(rec["tables"], 14)\n'
        '        self.assertEqual(rec["columns"], 3)\n'
        '        self.assertEqual(rec["verified"], 62)\n'
        '        self.assertEqual(rec["unverified"], 54)\n'
        '        self.assertFalse(rec["complete_input"])\n'
        '        self.assertIn("world.plans.plan_id", rec["promoted"])\n'
        '        self.assertEqual(len(rec["promoted"]), 8)\n'
    )
    text = replace_once(text, old, new, "freeze test_t193 inventory")
    p.write_text(text, encoding="utf-8")


def patch_inventory():
    raw = SRC.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("inventory src has BOM")
    text = raw.decode("utf-8")
    reps = [
        (
            "| world.own_units.order.type | 未验证 | 师当前任务类型。空路径不能证明待机；非空路径也还不是 OrderType，commandlist 在邻省行军后仍为空。 |",
            "| world.own_units.order.type | 未验证 | 师当前任务类型。空路径不能证明待机；非空路径也还不是 OrderType。邻省行军以及短时 1x 后 commandlist 仍为空，不把非空路径当成 OrderType。 |",
        ),
        (
            "| world.own_units.order.target_province_ids | 未验证 | 师当前任务的目标省份。邻省行军后 CArmy+0x220 full_path 仍为空，不把路径末省推断成 target。 |",
            "| world.own_units.order.target_province_ids | 未验证 | 师当前任务的目标省份。邻省行军以及短时 1x 后 CArmy+0x220 full_path 仍为空，不把路径末省推断成 target。 |",
        ),
        (
            "| world.own_units.order.eta | 未验证 | 该师当前命令的预计到达时间或进度。邻省行军后 CArmy+0x240 在暂停下仍为 0，不升格。 |",
            "| world.own_units.order.eta | 未验证 | 该师当前命令的预计到达时间或进度。邻省行军后 CArmy+0x240 在暂停下仍为 0；短时 1x 后该槽为 0x000041a0（16800），不是 0-1 进度，不升格。 |",
        ),
        (
            "| world.plans.vertex_province_ids | 未验证 | 计划有序折线控制点。 |",
            "| world.plans.vertex_province_ids | 未验证 | 计划有序折线控制点。官方 path 在 COrderInstance+0x70（token 0x174）。COrderNewFrontCommand Post 成功后该数组仍为空；+0x258/+0x25c 不是官方 vertex/path。 |",
        ),
        (
            "| world.plans.assigned_unit_ids | 未验证 | 计划绑定的师编号。 |",
            "| world.plans.assigned_unit_ids | 已验证 | 计划绑定的师编号，取自 COrderInstance+0x210 数组（官方 writer 0x10d1450 token scheduled_member 0x30b1）。元素经 vt+0x20 / this-adjust +0xB8 还原为 CArmy，编号在 +0x1C。COrderAssignCommand 后对照为师 1838。 |",
        ),
        (
            "| world.plans.executing | 未验证 | 计划是否正在执行。 |",
            "| world.plans.executing | 已验证 | 计划是否正在执行，取自 COrderInstance+0x248。官方 token 为 can_execute（0x30b2，非零才写出）；COrderExecuteCommand 把该字节写成 execute_order。活体在保持官方暂停下由 0 变为 1。 |",
        ),
    ]
    for old, new in reps:
        text = replace_once(text, old, new, old[:40])
    if "附录" in text:
        raise SystemExit("appendix slipped in")
    lines = text.splitlines()
    n_tables = sum(1 for ln in lines if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
    n_fields = sum(1 for ln in lines if ln.startswith("| ") and not ln.startswith("| 字段名 |") and not ln.startswith("| ---"))
    n_verified = sum(1 for ln in lines if "| 已验证 |" in ln)
    n_unverified = sum(1 for ln in lines if "| 未验证 |" in ln)
    if n_tables != 14 or n_fields != 116 or n_verified != 64 or n_unverified != 52:
        raise SystemExit(f"inventory counts wrong: tables={n_tables} fields={n_fields} v={n_verified} u={n_unverified}")
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    STAGE.write_bytes(text.encode("utf-8"))
    shutil.copyfile(STAGE, INV_D)
    raw_d = INV_D.read_bytes()
    if raw_d.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("D inventory gained a BOM")
    sha = hashlib.sha256(raw_d).hexdigest()
    if raw_d != text.encode("utf-8"):
        raise SystemExit("D inventory does not match staged text")
    rec = {
        "updated": True,
        "sha256": sha,
        "fields": 116,
        "tables": 14,
        "columns": 3,
        "verified": 64,
        "unverified": 52,
        "complete_input": False,
        "promoted": [
            "world.plans.assigned_unit_ids",
            "world.plans.executing",
        ],
        "authorized_by": AUTHORIZED,
    }
    (ROOT / "research" / "t196_inventory_sha256.json").write_text(
        json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return rec


def write_evidence():
    ev = {
        "authorized_by": AUTHORIZED,
        "pid": 12948,
        "exe_sha256": "709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148",
        "promoted": [
            "world.plans.assigned_unit_ids",
            "world.plans.executing",
        ],
        "not_promoted": [
            "world.plans.type",
            "world.plans.vertex_province_ids",
            "world.plans.axis_province_ids",
            "world.plans.status",
            "world.own_units.order.type",
            "world.own_units.order.target_province_ids",
            "world.own_units.order.eta",
            "world.leaders.assigned_to kind=unit",
        ],
        "scaffolding_only": [
            "world.own_units.path_province_ids",
            "formation.army_id",
            "world.armies.*",
            "formation.army_group_id",
            "world.army_groups.*",
            "world.plans.plan_id",
            "world.plans.assigned_army_ids",
        ],
        "live": {
            "plan_id": 1,
            "assigned_army_ids": [1],
            "assigned_unit_ids": [1838],
            "executing": True,
            "type_30": 2,
            "path_70": [],
            "field_258_25c": [5097, 7944],
            "pause": 1,
            "speed": 0,
        },
        "notes": {
            "scheduled_member": "COrderInstance+0x210 token 0x30b1; COrderAssignCommand then unit 1838 via this-adjust +0xB8",
            "executing": "COrderExecuteCommand wrote +0x248 0->1 while officially paused; token can_execute 0x30b2",
            "newfront": "COrderNewFrontCommand post_rax=1 but no new instance and official +0x70 still empty",
            "set_army_leader": "IsValid+Post rax=1 for 312/313 and unit 314->1846; mid-snapshots had +0x88 set; theatre_final and live +0x88/+0x1048 were 0. Do not treat unit-handle SetArmyLeader as proven.",
            "order_1x": "CPauseGame 12:00->13:00; 1829 still at 5010 path [8036]; commandlist/full_path empty; +0x240=0x000041a0",
        },
    }
    (ROOT / "research" / "t196_plan_execute_assign.json").write_text(
        json.dumps(ev, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main():
    patch_own_plans()
    patch_offsets_py()
    patch_offsets_json()
    freeze_test_t193()
    rec = patch_inventory()
    write_evidence()
    print(json.dumps({"ok": True, "inventory": rec}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
