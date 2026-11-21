import json
from pathlib import Path
sch=json.loads(Path("calling/tables/generalissimo_input.schema.json").read_text(encoding="utf-8"))
for k in ("Order","OrderType"):
    print("===== ",k)
    print(json.dumps(sch["$defs"][k], indent=2, ensure_ascii=False))
