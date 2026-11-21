from pathlib import Path
import hashlib

INV=Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
STAGE_DIR=Path(r"C:\Users\Lenovo\agent-tools")
STAGE=STAGE_DIR/"态势信息读取能力清单.md"
raw=INV.read_bytes()
print("sha_before", hashlib.sha256(raw).hexdigest(), "nl", b"\r\n" in raw)
text=raw.decode("utf-8")
nl="\r\n" if b"\r\n" in raw else "\n"
repls={
"| world.own_units.formation.army_group_id | 未验证 | 师所属集团军群编号。 |":
"| world.own_units.formation.army_group_id | 已验证 | 师所属集团军群编号。由 CArmy+0xC0 的集团军再经 COrdersGroup+0x1B8 的 CArmyGroup* 取得，并与集团军群 +0x230 下属表互证。无集团军群时为空。 |",

"| world.army_groups.army_group_id | 未验证 | 集团军群编号。 |":
"| world.army_groups.army_group_id | 已验证 | 集团军群编号，取自 CTheatre+0x98 下 CArmyGroup 句柄 id（类型 53，与集团军相同，需靠 RTTI 区分）。 |",

"| world.army_groups.name | 未验证 | 集团军群名称。 |":
"| world.army_groups.name | 已验证 | 集团军群名称，取自 CArmyGroup+0x160；新建后为默认本地化名。 |",

"| world.army_groups.leader_id | 未验证 | 集团军群司令编号。 |":
"| world.army_groups.leader_id | 已验证 | 集团军群司令编号，取自 CArmyGroup+0x88 将领指针的句柄 id；未任命时为空。 |",

"| world.army_groups.army_ids | 未验证 | 集团军群下属集团军编号。 |":
"| world.army_groups.army_ids | 已验证 | 集团军群下属集团军编号，取自 CArmyGroup+0x230 的 COrdersGroup* 数组。 |",

"| world.armies.plan_id | 未验证 | 集团军绑定的计划编号。 |":
"| world.armies.plan_id | 已验证 | 集团军绑定的计划编号，取自 COrdersGroup+0x98 的 COrderInstance 的 instance_id（+0x244）。无计划时为空。 |",

"| world.plans.plan_id | 未验证 | 玩家计划对象编号。 |":
"| world.plans.plan_id | 已验证 | 玩家计划对象编号，取自挂在 COrdersGroup+0x98 上的 COrderInstance+0x244；不是边境 CFront。 |",

"| world.plans.assigned_army_ids | 未验证 | 计划绑定的集团军编号。 |":
"| world.plans.assigned_army_ids | 已验证 | 计划绑定的集团军编号，取自该 COrderInstance 所挂的 COrdersGroup 句柄 id。 |",

"| world.leaders.assigned_to | 已验证 | 将领任职目标，取自 CArmyLeader+0x1048 的 {type,id} 句柄；类型 53 表示集团军。不是 +0x1068 的 deployed 布尔，任命后该布尔仍可为 0。 |":
"| world.leaders.assigned_to | 已验证 | 将领任职目标，取自 CArmyLeader+0x1048 的 {type,id} 句柄。类型 53 为集团军与集团军群共用，需按 RTTI 解析为 army 或 army_group。不是 +0x1068 的 deployed 布尔，任命后该布尔仍可为 0。 |",
}
missing=[a for a in repls if a not in text]
if missing:
    print("MISSING")
    for m in missing:
        print("WANT", m)
        key=m.split("|")[1].strip()
        for ln in text.splitlines():
            if key in ln:
                print("HAVE", ln)
    raise SystemExit(1)
new_text=text
for a,b in repls.items():
    new_text=new_text.replace(a,b,1)
field_rows=[]
for ln in new_text.splitlines():
    parts=[p.strip() for p in ln.split("|")]
    if len(parts)>=4 and parts[1] and parts[2] in ("已验证","未验证"):
        field_rows.append((parts[1],parts[2],parts[3]))
n_tables=sum(1 for ln in new_text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
verified=sum(1 for n,s,d in field_rows if s=="已验证")
unverified=sum(1 for n,s,d in field_rows if s=="未验证")
print("tables",n_tables,"fields",len(field_rows),"verified",verified,"unverified",unverified)
assert n_tables==14 and len(field_rows)==116
assert verified==62 and unverified==54
assert "附录" not in new_text
data=new_text.replace("\r\n","\n")
if nl=="\r\n":
    data=data.replace("\n","\r\n")
out=data.encode("utf-8")
STAGE_DIR.mkdir(parents=True, exist_ok=True)
STAGE.write_bytes(out)
print("staged", len(out))
