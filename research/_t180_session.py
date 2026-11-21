"""t180 session recheck. Read-only, no game-method execution."""
from __future__ import annotations
import os, sys, json
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc, find_pid
from pe import PE
from gamestate import detect_session, resolve_player_country, read_campaign_summary

out={'expected_pid':26976,'read_only':True,'no_game_method_execution':True}
pid=find_pid('hoi4.exe')
out['pid']=pid
if not pid:
    out.update({'in_game':False,'stop':True,'reason':'no hoi4.exe'})
    Path('research/t180_session_recheck.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print('NO HOI4')
    raise SystemExit(0)
pe=PE(r'D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe')
P=Proc(pid)
try:
    session=detect_session(P,pe)
    gs_hex=(session.get('signals') or {}).get('gs_ptr')
    gs_ptr=int(gs_hex,16) if isinstance(gs_hex,str) else None
    country=resolve_player_country(P,gs_ptr) if gs_ptr else {'ok':False}
    summary=read_campaign_summary(P,gs_ptr) if gs_ptr else {}
    fields=(summary or {}).get('fields') or {}
    date=(fields.get('date_full') or {})
    out.update({
        'pid_matches': pid==26976,
        'in_game': bool(session.get('in_game')),
        'session': session.get('session'),
        'tag': country.get('tag'),
        'player_index': country.get('player_index'),
        'country_ptr': country.get('country_ptr'),
        'date': date,
        'hour_tick': (date or {}).get('hour_tick') or fields.get('date_hour_tick_0x468'),
        'speed_index': fields.get('game_speed_index'),
        'speed_notch': fields.get('game_speed_notch'),
        'stop': not bool(session.get('in_game')),
    })
    Path('research/t180_session_recheck.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('pid','pid_matches','in_game','session','tag','player_index','hour_tick','speed_index','speed_notch','date')},indent=2,default=str))
finally:
    P.close()
