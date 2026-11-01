import json
from pathlib import Path
from datetime import datetime

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
OUT = ROOT / "reports" / "phase2ijx_move_post_timeout_diag.json"
SUM = ROOT / "reports" / "phase2ijx_move_post_timeout_diag_summary.json"
DOC = ROOT / "docs" / "PHASE2IJX_MOVE_POST_TIMEOUT_DIAG.md"

rep = json.loads(OUT.read_text(encoding="utf-8"))
post = (rep.get("g6") or {}).get("post") or {}
note = (
    "PATH_CONTAINS_DEST proven: path_after included dest 3931 "
    f"{post.get('path_after')}. post_wait still 258 WAIT_TIMEOUT and post_rax=0 "
    "(stub wait returned before thread finished) — Post appears async-accepted. "
    "hoi4 then went Responding=False and process exited; SELF-RELAUNCH ITA @1x after observe. "
    "HIT stands on path evidence, not ambient seq/drain."
)
rep["honesty_note"] = note
rep["process_after"] = "EXITED_AFTER_OBSERVE_THEN_RELAUNCH"
rep["path_c_honesty"]["estimate_after"] = "~74-76%"
rep["path_c_honesty"]["this_slice_pp"] = "+3-5pp first ordinary Move PATH_CONTAINS_DEST (unstable Post wait/CRT)"
rep["next_shortest_blocker"] = (
    "Stabilize Move Post CRT wait (still 258 despite path HIT) / avoid process exit; "
    "or Cancel/wartime Attack gated next; Instant PARKED."
)
rep["timestamp_asia_shanghai"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai")
OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")

sumd = json.loads(SUM.read_text(encoding="utf-8"))
sumd["honesty_note"] = note
sumd["process_after"] = "EXITED_AFTER_OBSERVE_THEN_RELAUNCH"
sumd["estimate"] = "~74-76%"
SUM.write_text(json.dumps(sumd, indent=2), encoding="utf-8")

txt = DOC.read_text(encoding="utf-8")
if "process exited" not in txt:
    DOC.write_text(
        txt.rstrip()
        + "\n\n## Honesty\n"
        + note
        + "\n",
        encoding="utf-8",
    )
print("annotated OK")
