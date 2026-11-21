from pathlib import Path
import shutil, hashlib, json, os, sys

INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
STAGE_DIR = Path(r"C:\Users\Lenovo\agent-tools")
STAGE = STAGE_DIR / "态势信息读取能力清单.md"

text = INV.read_text(encoding="utf-8")
# keep newline style
raw = INV.read_bytes()
nl = "\r\n" if b"\r\n" in raw else "\n"
print("newline", repr(nl), "BOM", raw[:3], "sha_before", hashlib.sha256(raw).hexdigest())

repls = {
    "| world.own_units.formation.army_id | 未验证 | 师所属集团军编号。 |":
    "| world.own_units.formation.army_id | 已验证 | 师所属集团军编号，取自 CArmy+0xC0 的 COrdersGroup*；与该集团军成员表互证。无集团军时为空，不能把战区师表当成此项。 |",

    "| world.armies.army_id | 未验证 | 集团军编号。 |":
    "| world.armies.army_id | 已验证 | 集团军编号，取自 CTheatre+0x80 下 COrdersGroup 句柄 id（类型 53）。 |",

    "| world.armies.name | 未验证 | 集团军名称。 |":
    "| world.armies.name | 已验证 | 集团军名称，取自 COrdersGroup+0x160；新建后为默认本地化名。 |",

    "| world.armies.leader_id | 未验证 | 集团军司令编号。 |":
    "| world.armies.leader_id | 已验证 | 集团军司令编号，取自 COrdersGroup+0x88 将领指针的句柄 id；未任命时为空。 |",

    "| world.armies.unit_ids | 未验证 | 编入集团军的师编号。 |":
    "| world.armies.unit_ids | 已验证 | 编入集团军的师编号，取自 COrdersGroup+0x50 成员指针经虚函数回主对象后的 CArmy 句柄。 |",

    "| world.leaders.assigned_to | 未验证 | 将领当前任职的集团军、集团军群或师。 |":
    "| world.leaders.assigned_to | 已验证 | 将领任职目标，取自 CArmyLeader+0x1048 的 {type,id} 句柄；类型 53 表示集团军。不是 +0x1068 的 deployed 布尔，任命后该布尔仍可为 0。 |",
}

missing = [a for a in repls if a not in text]
if missing:
    print("MISSING LINES:")
    for m in missing:
        print(" ", m)
    # show close lines
    for ln in text.splitlines():
        if any(k in ln for k in ("formation.army_id", "world.armies.", "assigned_to")):
            print("HAVE:", ln)
    raise SystemExit(1)

new_text = text
for a,b in repls.items():
    new_text = new_text.replace(a, b, 1)

# counts
rows = [ln for ln in new_text.splitlines() if ln.startswith("| ") and "字段名" not in ln and not ln.startswith("| ---") and not ln.startswith("| --")]
# better: field rows have three cols and a dotted field or chinese? Official fields start with world. or meta. or policy. or feedback.
field_rows = []
for ln in new_text.splitlines():
    parts = [p.strip() for p in ln.split("|")]
    # ['', name, status, desc, '']
    if len(parts) >= 4 and parts[1] and parts[2] in ("已验证", "未验证"):
        field_rows.append((parts[1], parts[2], parts[3]))

n_tables = sum(1 for ln in new_text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
verified = sum(1 for n,s,d in field_rows if s=="已验证")
unverified = sum(1 for n,s,d in field_rows if s=="未验证")
print("tables", n_tables, "fields", len(field_rows), "verified", verified, "unverified", unverified)
assert n_tables == 14 and len(field_rows) == 116
assert verified == 54 and unverified == 62
assert "附录" not in new_text
# confirm promotions
for name in [
    "world.own_units.formation.army_id",
    "world.armies.army_id",
    "world.armies.name",
    "world.armies.leader_id",
    "world.armies.unit_ids",
    "world.leaders.assigned_to",
]:
    row = next(x for x in field_rows if x[0]==name)
    assert row[1]=="已验证", row
# still unverified
for name in [
    "world.own_units.formation.army_group_id",
    "world.army_groups.army_group_id",
    "world.armies.plan_id",
    "world.own_units.order.type",
]:
    row = next(x for x in field_rows if x[0]==name)
    assert row[1]=="未验证", row

# write staging with same newline / no extra BOM unless original had it
had_bom = raw.startswith(b"\xef\xbb\xbf")
data = new_text.replace("\r\n","\n")
if nl == "\r\n":
    data = data.replace("\n", "\r\n")
out = data.encode("utf-8")
if had_bom:
    out = b"\xef\xbb\xbf" + out
STAGE_DIR.mkdir(parents=True, exist_ok=True)
STAGE.write_bytes(out)
print("staged", STAGE, "bytes", len(out))
