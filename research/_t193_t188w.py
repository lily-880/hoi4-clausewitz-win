import json
from pathlib import Path
# t188 writer details for type names and extra fields
w=json.loads(Path("research/t188_plan_writers.json").read_text(encoding="utf-8"))
print(json.dumps(w, ensure_ascii=False, indent=2)[:8000])
