from pathlib import Path
import re, json
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md").read_text(encoding="utf-8")
rows=[]
current_table=None
for ln in inv.splitlines():
    if ln.startswith("## ") or ln.startswith("# "):
        current_table=ln.lstrip("# ").strip()
    m=re.match(r"^\| ([^|]+?) \| (已验证|未验证) \| (.*) \|$", ln)
    if m:
        rows.append({"table": current_table, "field": m.group(1).strip(), "status": m.group(2), "note": m.group(3).strip()})
unver=[r for r in rows if r["status"]=="未验证"]
ver=[r for r in rows if r["status"]=="已验证"]
print("total", len(rows), "verified", len(ver), "unverified", len(unver))
print("=== 未验证 ===")
for r in unver:
    print(f"{r['field']} | {r['note']}")
Path("research/t190_unverified_fields.json").write_text(json.dumps(unver, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
