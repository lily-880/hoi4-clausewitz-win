#!/usr/bin/env python3
"""Minimal MCP stdio stub for Phase 1 (doctor/status only).

Not a full 107-tool port. Transport: JSON-RPC 2.0 over stdio (MCP 2024-11-05).
"""
from __future__ import annotations

import json
import os
import platform
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "calling"))

PROTOCOL = "2024-11-05"


def _tool_list():
    return [
        {
            "name": "hoi4_win_doctor",
            "description": "Check HOI4 install paths and optionally attach read-only to hoi4.exe.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "hoi4_win_status",
            "description": "Attach and report proven live facts, including the campaign date.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "hoi4_win_redeploy",
            "description": "Strategic-redeploy one army to a province. Set dry_run to only check IsValid.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "army": {"type": "integer"},
                    "province": {"type": "integer"},
                    "dry_run": {"type": "boolean"},
                },
                "required": ["army", "province"],
            },
        },
    ]


def _run_doctor():
    import io
    from contextlib import redirect_stdout
    # reuse CLI
    sys.path.insert(0, ROOT)
    import clausewitz_win as cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.cmd_doctor(None)
    return {"exit_code": code, "output": buf.getvalue()}


def _run_status():
    import io
    from contextlib import redirect_stdout
    sys.path.insert(0, ROOT)
    import clausewitz_win as cli

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.cmd_status(None)
    return {"exit_code": code, "output": buf.getvalue()}


def _run_redeploy(args):
    import strategic_order
    return strategic_order.strategic_redeploy(
        int(args["army"]),
        int(args["province"]),
        dry_run=bool(args.get("dry_run")),
    )


HANDLERS = {
    "hoi4_win_doctor": lambda args: _run_doctor(),
    "hoi4_win_status": lambda args: _run_status(),
    "hoi4_win_redeploy": lambda args: _run_redeploy(args),
}


def reply(msg_id, result=None, error=None):
    out = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        out["error"] = error
    else:
        out["result"] = result
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method")
        msg_id = req.get("id")
        params = req.get("params") or {}
        if method == "initialize":
            reply(
                msg_id,
                {
                    "protocolVersion": PROTOCOL,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "hoi4-clausewitz-win",
                        "version": "0.1.0",
                        "platform": platform.system(),
                    },
                },
            )
        elif method == "tools/list":
            reply(msg_id, {"tools": _tool_list()})
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            fn = HANDLERS.get(name)
            if not fn:
                reply(msg_id, error={"code": -32601, "message": "unknown tool %s" % name})
                continue
            try:
                result = fn(args)
                reply(
                    msg_id,
                    {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2)}
                        ]
                    },
                )
            except Exception as e:
                reply(msg_id, error={"code": -32000, "message": str(e)})
        elif method == "notifications/initialized":
            continue
        elif msg_id is not None:
            reply(msg_id, error={"code": -32601, "message": "method not found"})


if __name__ == "__main__":
    main()
