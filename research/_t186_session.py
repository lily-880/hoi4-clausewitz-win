import sys,os,json,hashlib,re
from pathlib import Path
sys.path.insert(0,"calling")
from pe import PE
from mem import Proc, find_pid
from gamestate import detect_session, resolve_player_country, read_campaign_summary, _pdx_array, _rtti_name_from_vtable
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"

INV=Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
raw=INV.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
text=raw.decode("utf-8")
rows=[ln for ln in text.splitlines() if re.match(r"^\| [^|]+ \| (已验证|未验证) \|", ln)]
# wars / pause / plans / crises / visibility / building damage
keys=("war","pause","plan","front","cris","visib","fog","fow","damag","building","paused","intel")
print("SHA", sha, "rows", len(rows))
print("--- inventory hits ---")
for ln in rows:
    low=ln.lower()
    if any(k in low for k in keys) or "战争" in ln or "暂停" in ln or "计划" in ln or "危机" in ln or "可见" in ln or "迷雾" in ln or "受损" in ln or "等级" in ln:
        print(ln)

p=Proc(find_pid("hoi4.exe"))
pe=PE(p.image_path)
try:
    session=detect_session(p, pe)
    gs=int(session["signals"]["gs_ptr"],16)
    res=resolve_player_country(p, gs)
    co=int(res["country_ptr"],16)
    summary=read_campaign_summary(p, gs)
    fields=summary.get("fields",{}) if isinstance(summary, dict) else {}
    ver=summary.get("verified",{}) if isinstance(summary, dict) else {}
    rec={
        "pid": p.pid,
        "in_game": bool(session.get("in_game")),
        "idler": session.get("signals",{}).get("idler_class") or session.get("idler"),
        "country_ptr": hex(co),
        "gs_ptr": hex(gs),
        "tag": ver.get("player_tag_letter") or fields.get("player_tag_letter"),
        "player_index": ver.get("player_tag") or (fields.get("player_resolve") or {}).get("player_index"),
        "date": (ver.get("date_full") or {}),
        "speed_notch": ver.get("game_speed_notch"),
        "hour_tick": (ver.get("date_full") or {}).get("hour_tick") or fields.get("date_hour_tick_0x468"),
        "armies_size": _pdx_array(p, co+0x290)["size"],
        "gs_combats_size": _pdx_array(p, gs+0x268)["size"],
        "read_only": True,
    }
    Path("research/t186_session_recheck.json").write_text(json.dumps(rec, indent=2, default=str, ensure_ascii=False)+"\n", encoding="utf-8")
    print("--- session ---")
    print(json.dumps(rec, indent=2, default=str, ensure_ascii=False))
finally:
    p.close()
