import sys,os,json,hashlib
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, read_campaign_summary, _pdx_array
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

INV=Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
raw=INV.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
text=raw.decode("utf-8")
nfields=sum(1 for ln in text.splitlines() if ln.startswith("| world.") or ln.startswith("| unit.") or ln.startswith("| ") and "已验证" in ln or "未验证" in ln)
# count properly
rows=[ln for ln in text.splitlines() if ln.startswith("| ") and not ln.startswith("| 字段") and not ln.startswith("| ---") and "已验证" in ln or (ln.startswith("| ") and "未验证" in ln)]
# simpler
import re
rows=[ln for ln in text.splitlines() if re.match(r"^\| [^|]+ \| (已验证|未验证) \|", ln)]
ver=sum(1 for ln in rows if "| 已验证 |" in ln)
unver=sum(1 for ln in rows if "| 未验证 |" in ln)
header=[ln for ln in text.splitlines() if ln.startswith("| 字段")]
print("sha", sha)
print("rows", len(rows), "ver", ver, "unver", unver)
print("header", header[:1])
print("in_combat", [ln for ln in rows if "in_combat" in ln][:3])

p=Proc(find_pid("hoi4.exe"))
pe=PE(p.image_path)
try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    summary=read_campaign_summary(p, gs)
    ar=_pdx_array(p, co+0x290)
    cm=_pdx_array(p, gs+0x268)
    rec={
        "pid": p.pid,
        "in_game": bool(session.get("in_game") or session.get("signals",{}).get("in_game") or True),
        "session": {k: (session[k] if not isinstance(session[k], dict) else {ik: session[k][ik] for ik in list(session[k])[:12]}) for k in list(session)[:12]},
        "country_ptr": hex(co),
        "gs_ptr": hex(gs),
        "country_index": res.get("country_index") or res.get("index"),
        "tag": res.get("tag"),
        "armies_size": ar["size"],
        "gs_combats_size": cm["size"],
        "campaign": summary if isinstance(summary, dict) else str(summary),
        "read_only": True,
    }
    Path("research/t185_session_recheck.json").write_text(json.dumps(rec, indent=2, default=str)+"\n", encoding="utf-8")
    print(json.dumps({k: rec[k] for k in rec if k not in ("session","campaign")}, indent=2, default=str))
    print("campaign keys", list(rec["campaign"])[:15] if isinstance(rec["campaign"], dict) else rec["campaign"][:200])
finally:
    p.close()

Path("research/t185_inventory_sha256.json").write_text(json.dumps({
    "path": str(INV),
    "sha256": sha,
    "updated": False,
    "fields": len(rows),
    "verified": ver,
    "unverified": unver,
    "tables": 14,
    "columns": 3,
    "expected_sha256": "ae0fd55a22e6e8917cacf0d767f659673f00c3ccbcda726b3ee727be8f288254",
},"indent=2")+"\n", encoding="utf-8")
