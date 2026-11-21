import json
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import sys
sys.path.insert(0,"calling")
from pe import PE

pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
cs=Cs(CS_ARCH_X86, CS_MODE_64)
bind=json.loads(Path("research/t194_bind_cmds.json").read_text(encoding="utf-8"))

for name in ["CPauseGame","COrderExecuteCommand","COrderAssignCommand","COrderNewFrontCommand","CCreateAreaDefenseCommand","COrderSetPathCommand","COrderNewFallbackCommand"]:
    rec=bind["cmds"][name]
    print(f"\n#### {name} factory={rec.get('factory')} size={rec.get('size')} isvalid={rec.get('isvalid')} execute={rec.get('execute')} vt={rec.get('vts')}")

# print execute clips (first 80 already may be in files)
for name in ["CPauseGame","COrderExecuteCommand","COrderAssignCommand","COrderNewFrontCommand","CCreateAreaDefenseCommand"]:
    rec=bind["cmds"][name]
    exe=rec.get("execute")
    if not exe: continue
    path=Path(f"research/_t194_clip_{name}_execute_{exe}.txt")
    print("\n"+"="*80, "EXECUTE", name, exe)
    if path.exists():
        lines=path.read_text(encoding="utf-8").splitlines()
        print("lines", len(lines))
        print("\n".join(lines[:90]))
