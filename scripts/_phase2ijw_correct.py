import json
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
OUT = ROOT / "reports" / "phase2ijw_min_safe_move_post.json"
SUM = ROOT / "reports" / "phase2ijw_min_safe_move_post_summary.json"
DOC = ROOT / "docs" / "PHASE2IJW_MIN_SAFE_MOVE_POST.md"
SAFE = ROOT / "docs" / "SAFE_POST_ENABLE_CHECKLIST.md"
LAND = ROOT / "docs" / "LAND_POST_READINESS.md"
CHECK = ROOT / "research" / "safe_enable_checklist.json"

rep = json.loads(OUT.read_text(encoding="utf-8"))
post = (rep.get("g6") or {}).get("post") or {}
obs = (rep.get("g6") or {}).get("observe") or {}
honest = "G6_MOVE_POST_TIMEOUT"
note = (
    "FN_CMD_QUEUE_POST WaitForSingleObject returned WAIT_TIMEOUT(258); post_rax=0; "
    "path empty before/after; province stayed 6906; seq_delta=3/drain_delta=13 treated as ambient "
    "NOT acceptance. Dry-run IsValid=1 for dest 3931 PROVEN. Initial script label ACCEPTED_WEAK OVERCLAIMED; corrected."
)
rep["result"] = honest
rep["honesty_correction"] = {
    "prior_label": "G6_MOVE_POST_ACCEPTED_WEAK",
    "reason": note,
    "post_wait": post.get("post_wait"),
    "WAIT_TIMEOUT": 258,
    "path_evidence": False,
    "province_changed": obs.get("province_changed"),
    "seq_delta_ambient": obs.get("seq_delta"),
}
rep["path_c_honesty"] = {
    "baseline_band": "~60%",
    "after_2iju_2ijv": "~71-73%",
    "crossed_70": True,
    "estimate_after": "~71-73%",
    "this_slice_pp": "+0-1pp plumbing (Move IsValid+G5 safe_land gate); live Move Post NOT HIT",
}
rep["next_shortest_blocker"] = (
    "Move FN_CMD_QUEUE_POST times out (wait=258) after IsValid=1; diagnose queue hang vs pause-during-inject, "
    "or compare Strategic post path (HIT in 2iju). Do NOT endless midflight poll. Instant PARKED."
)
rep["timestamp_asia_shanghai"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai")
OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")

sumd = json.loads(SUM.read_text(encoding="utf-8"))
sumd["result"] = honest
sumd["estimate"] = "~71-73%"
sumd["honesty_note"] = note
sumd["g6_timeout"] = True
SUM.write_text(json.dumps(sumd, indent=2), encoding="utf-8")

ts = datetime.now().strftime("%Y-%m-%d %H:%M Asia/Shanghai")
DOC.write_text(
    f"""# Phase 2ijw — Minimum safe Move Post (G4→G5→G6)

**Result:** `{honest}` (corrected; prior ACCEPTED_WEAK overclaimed)
**Posts:** move=1 strategic=0
**allow_post final:** False

## G4/G5
- Env CLAUSEWITZ_ALLOW_POST=1 in Post process only then cleared
- Marker research/safe_land_tool_gate.OPEN (Move 1402 + Strategic 4753) then unlinked
- allow_post: env-only False → env+marker True → restored False

## G6 Move
- Factory 1402 / calling/move_order.py
- Dry-run IsValid HIT: army 1042 @ province 6906 → dest 3931
- Live Post: POSTED_DEST_NOT_IN_PATH with post_wait=258 (WAIT_TIMEOUT); post_rax=0; path []; province unchanged
- Observe deltas (seq+3, drain+13) treated as ambient, not acceptance

## Path C
estimate_after=~71-73%; crossed_70=True; live Move Post not proven

*Phase 2ijw — {ts}*
""",
    encoding="utf-8",
)

txt = SAFE.read_text(encoding="utf-8")
idx = txt.rfind("## Phase 2ijw")
if idx >= 0:
    head = txt[:idx].rstrip()
else:
    head = txt.rstrip()
block = """

---

## Phase 2ijw — Move Post (factory 1402) gated once

**Result:** `G6_MOVE_POST_TIMEOUT` (WAIT_TIMEOUT on FN_CMD_QUEUE_POST; corrected from ACCEPTED_WEAK)

Marker: `research/safe_land_tool_gate.OPEN` (Move+Strategic). Restored CLOSED after one-shot.

| ID | State |
| --- | --- |
| G4 | PROVEN_ONCE env CLAUSEWITZ_ALLOW_POST=1 then restored |
| G5 | OPEN_SAFE_LAND_MOVE_STRATEGIC then CLOSED_NOT_OPENED |
| G6-Move | TIMEOUT — IsValid dry HIT; live Post wait=258; no PATH_CONTAINS_DEST |

"""
SAFE.write_text(head + "\n" + block, encoding="utf-8")

lt = LAND.read_text(encoding="utf-8")
lt2 = re.sub(r"\n---\n\n##[^\n]*2ijw[\s\S]*$", "", lt.rstrip())
block_land = """

---

## §2ijw — Ordinary Move Post attempt (factory 1402)

- `calling/move_order.py`: CMoveCommand factory **1402** / RVA `0x13FB000` / action VT `0x2A1F648`
- Province array via remote VirtualAllocEx u32[1] (not freed after live Post — UAF avoid)
- Gate: env + `safe_land_tool_gate.OPEN` → Post → restore False
- Dry-run IsValid=1 for army 1042 → dest 3931 **PROVEN**
- Live Post: WAIT_TIMEOUT(258) on FN_CMD_QUEUE_POST; path empty; province 6906 unchanged → **G6_MOVE_POST_TIMEOUT**
- Instant PARKED; Attack/Cancel not opened this slice

"""
LAND.write_text(lt2 + "\n" + block_land, encoding="utf-8")

ch = json.loads(CHECK.read_text(encoding="utf-8"))
for g in ch.get("gaps", []):
    if g.get("id") == "command_queue_tool_gate":
        g["proven_once_move"] = {
            "phase": "2ijw",
            "factory_idx": 1402,
            "result": "G6_MOVE_POST_TIMEOUT",
            "isvalid_dry": True,
            "post_wait": 258,
            "note": "IsValid dry HIT; live Post timed out — not PATH_CONTAINS_DEST",
        }
        g["status"] = "CLOSED_NOT_OPENED"
CHECK.write_text(json.dumps(ch, indent=2), encoding="utf-8")
print("CORRECTED", honest)
print(
    "markers",
    (ROOT / "research" / "safe_land_tool_gate.OPEN").exists(),
    (ROOT / "research" / "strategic_only_tool_gate.OPEN").exists(),
)
