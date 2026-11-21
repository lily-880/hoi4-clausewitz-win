import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, "calling")
import config
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
raw = inv.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
text = raw.decode("utf-8")
n_tables = sum(1 for ln in text.splitlines() if ln.startswith("| 字段名 | 已验证/未验证 | 说明 |"))
fields = [ln for ln in text.splitlines() if ln.startswith("| ") and not ln.startswith("| 字段名 |") and not ln.startswith("| ---") and ln.count("|")>=4]
print(json.dumps({
    "sha256": sha,
    "tables": n_tables,
    "fields": len(fields),
    "verified": sum(1 for ln in fields if "| 已验证 |" in ln),
    "unverified": sum(1 for ln in fields if "| 未验证 |" in ln),
    "path_line": [ln for ln in fields if "path_province_ids" in ln][0],
    "type_line": [ln for ln in fields if "order.type |" in ln or "order.type |" in ln][0],
    "allow_post": config.allow_post(),
    "marker": Path("research/safe_land_tool_gate.OPEN").exists(),
}, ensure_ascii=False, indent=2))
