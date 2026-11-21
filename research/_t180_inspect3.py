from pathlib import Path
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
text = inv.read_text(encoding="utf-8")
# header first 20 and any count mentions
for i,l in enumerate(text.splitlines()[:25],1):
    print(f"{i}:{l}")
print("--- counts ---")
for i,l in enumerate(text.splitlines(),1):
    if any(k in l for k in ("41","75","116","14","已验证 ","未验证 ","字段")) and i<30:
        print(f"{i}:{l}")
# landindex summary
import json
ev=json.loads(Path("research/t180_landindex_and_edges.json").read_text(encoding="utf-8"))
print("landindex keys", ev.keys())
for k,v in ev.items():
    if k not in ("provinces","edges"):
        print(k, v if not isinstance(v,list) else f"list[{len(v)}]")
    elif k=="provinces":
        print("n provinces", len(v), "sample keys", v[0].keys() if v else None)
        print("first", v[0] if v else None)
# t179 checkpoint structure (head+tail)
ck=Path("research/t179_checkpoint.md").read_text(encoding="utf-8")
print("=== t179 ck len", len(ck), "lines", ck.count(chr(10)))
print("--- head ---")
print("\n".join(ck.splitlines()[:40]))
print("--- tail ---")
print("\n".join(ck.splitlines()[-40:]))
