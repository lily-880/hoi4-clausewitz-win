"""Read-only documentation of the Windows SP command Post -> Execute ABI.

Never posts. Call assert_post_allowed() before any future write path.
Proven against HOI4 1.19.4.1 (Operation Postern) on Windows — Haiti SP.
"""
from __future__ import annotations

from .config import assert_post_allowed, allow_post

# --- Proven RVAs (image-relative) ---
FN_CMD_QUEUE_POST = 0x22C41E0
FN_CMD_QUEUE_POST_SINK_DUMMY = 0x23F5CD0  # CDummyServer vt+0x28
FN_CMD_QUEUE_DRAIN_DUMMY = 0x23F64E0  # CDummyServer vt+0x30
FN_SESSION_UPDATE = 0x22C6410
FN_EXECUTE_LOOP = 0x22C4710
EXECUTE_SITE_A = 0x22C6C9D  # cmd.vt+0x50 inside session update
EXECUTE_SITE_B = 0x22C47DD  # second list

G_IDLER = 0x33DDB08
G_GAMESTATE = 0x33DD6B0
G_SESSION = 0x34FFBE8  # Phase 2ay: matches App+0x380 CSession* (live)

CDummyServer_VT = 0x2BCB040
CDummyServer_RING = 0xA0
CDummyServer_PENDING = 0x58  # head; tail +0x60; count +0x68
CDummyServer_EXECLIST = 0x40  # head; tail +0x48; count +0x50

CCommand_VT_ISVALID = 0x48
CCommand_VT_EXECUTE = 0x50
CCommand_VT_POSTEXEC = 0x58
CCommand_VT_CLONE = 0x68

CSession_SERVER = 0x40
CSession_STAGE_ARRAY = 0x48
CSession_STAGE_COUNT = 0x54
CSession_STATE = 0x30  # 2 = in-map SP
CSession_DRAIN_COUNTER = 0x60
CSession_EXEC_COUNTER = 0x6C8
CSession_EXECUTING_FLAG = 0x6CC

PIPELINE = (
    "UI/AI -> FN_CMD_QUEUE_POST(session, cmd) -> "
    "CDummyServer.vt+0x28 sink -> ring@+0xa0 -> "
    "SessionUpdate drain vt+0x30 -> pending@+0x58 -> "
    "stage session+0x48 -> IsValid vt+0x48 -> Execute vt+0x50 @ site A; "
    "optional execlist@+0x40 via loop B"
)


def post_command(backend, session: int, cmd: int) -> None:
    """Stub: posting remains DISABLED until safe_enable_checklist is closed."""
    assert_post_allowed()
    raise RuntimeError("unreachable: allow_post hard-denies")


def describe() -> dict:
    return {
        "posting": "DISABLED",
        "allow_post": allow_post(),
        "pipeline": PIPELINE,
        "FN_CMD_QUEUE_POST": hex(FN_CMD_QUEUE_POST),
        "G_SESSION": hex(G_SESSION),
        "CDummyServer_VT": hex(CDummyServer_VT),
    }
