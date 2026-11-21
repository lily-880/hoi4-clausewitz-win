from pathlib import Path
import json

# inventory line + t187 test/update pattern
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
text = inv.read_text(encoding="utf-8")
for i,l in enumerate(text.splitlines(),1):
    if "path_province" in l or "order.type" in l or "target_province" in l or "order.eta" in l or l.startswith("#") or "已验证" in l and i<15:
        print(f"{i:4d}|{l}")

print("======= t187 test head =======")
t = Path("research/test_t187_input_pause.py").read_text(encoding="utf-8")
print("\n".join(t.splitlines()[:80]))
print("======= offsets json pause key =======")
d = json.loads(Path("calling/tables/offsets_input_windows_1.19.5.json").read_text(encoding="utf-8-sig"))
print("pause_flag_t187", json.dumps(d.get("pause_flag_t187"), indent=2, ensure_ascii=False)[:1500])
