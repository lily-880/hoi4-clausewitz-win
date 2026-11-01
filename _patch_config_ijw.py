
from pathlib import Path
cfg = Path("calling/config.py")
t = cfg.read_text(encoding="utf-8")
start = t.index("def allow_post()")
end = t.index("def assert_post_allowed")
new = (
"def allow_post() -> bool:\n"
"    \"\"\"Requires CLAUSEWITZ_ALLOW_POST=1 AND land tool-gate marker.\n"
"\n"
"    Markers: research/safe_land_tool_gate.OPEN (Move+Strategic) or\n"
"    research/strategic_only_tool_gate.OPEN (Strategic-only legacy).\n"
"    Env alone never enough. NEVER_POST families forbidden by callers.\n"
"    \"\"\"\n"
"    if _os.environ.get(\'CLAUSEWITZ_ALLOW_POST\', \'\').strip() not in (\'1\', \'true\', \'TRUE\', \'yes\'):\n"
"        return False\n"
"    for name in (\'safe_land_tool_gate.OPEN\', \'strategic_only_tool_gate.OPEN\'):\n"
"        if _os.path.isfile(_os.path.join(ROOT, \'research\', name)):\n"
"            return True\n"
"    return False\n\n\n"
)
cfg.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("patched config")
