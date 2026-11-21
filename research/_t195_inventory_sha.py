import hashlib, json
from pathlib import Path

inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
raw = inv.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
text = raw.decode("utf-8")
field_rows = []
for ln in text.splitlines():
    parts = [p.strip() for p in ln.split("|")]
    if len(parts) >= 4 and parts[1] and parts[2] in ("已验证", "未验证"):
        field_rows.append((parts[1], parts[2]))
n_tables = sum(1 for ln in text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
verified = sum(1 for n, s in field_rows if s == "已验证")
unverified = sum(1 for n, s in field_rows if s == "未验证")
rec = {
    "updated": False,
    "reason": "no new live-proven fields this block; process crashed after COrderGroupCommand timeout",
    "sha256": sha,
    "expected_previous": "e4b7db714556524ac084c55367414e5f3ac55feb4b904bbb2fdec8ea866b75f0",
    "sha_unchanged": sha == "e4b7db714556524ac084c55367414e5f3ac55feb4b904bbb2fdec8ea866b75f0",
    "fields": len(field_rows),
    "tables": n_tables,
    "columns": 3,
    "verified": verified,
    "unverified": unverified,
    "complete_input": False,
    "promoted": [],
    "source": r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md",
}
out = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win\research\t195_inventory_sha256.json")
out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(rec, indent=2, ensure_ascii=False))
