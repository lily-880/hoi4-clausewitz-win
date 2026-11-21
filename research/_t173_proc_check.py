
import os,sys,json,hashlib,struct
from pathlib import Path
os.environ['CLAUSEWITZ_ALLOW_POST']='0'
os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'calling'))
from mem import Proc,find_pid
from pe import PE
from gamestate import detect_session,resolve_player_country,read_campaign_summary

profile=json.loads(Path('calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8-sig'))
p=None
try:
    try:
        p=Proc(find_pid('hoi4.exe'))
    except Exception as e:
        Path('research/t173_session_recheck.json').write_text(json.dumps({'stop':'no hoi4 process','error':str(e)},indent=2),encoding='utf-8')
        print(json.dumps({'stop':'no hoi4 process','error':str(e)})); raise SystemExit(0)
    h=hashlib.sha256()
    with open(p.image_path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    digest=h.hexdigest().upper()
    out={'pid':p.pid,'expected_pid':26976,'pid_matches':p.pid==26976,'path':p.image_path,'base':hex(p.base),'exe_sha256':digest,'fingerprint_matches':digest==profile['exe_sha256']}
    if not out['fingerprint_matches']:
        out['stop']='unknown executable fingerprint; no layout reads'
        Path('research/t173_session_recheck.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
        print(json.dumps(out)); raise SystemExit(0)
    pe=PE(p.image_path)
    session=detect_session(p,pe)
    out['session_name']=session.get('session')
    in_game=bool(session.get('in_game')) and session.get('session')=='in_game'
    if not in_game:
        out['stop']='HOI4 is running but not in a campaign. No new scan started; no campaign started or changed.'
        Path('research/t173_session_recheck.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
        print(json.dumps({'stop':out['stop'],'pid':p.pid,'session':session.get('session')},indent=2)); raise SystemExit(0)
    gs=int(session['signals']['gs_ptr'],16) if isinstance(session['signals']['gs_ptr'],str) else session['signals']['gs_ptr']
    fields=read_campaign_summary(p,gs)['fields']
    player=resolve_player_country(p,gs)
    out.update({'in_game':True,'gs':hex(gs),'player':player,'speed_index':fields.get('game_speed_index'),'speed_notch':fields.get('game_speed_notch'),'hour_progress':fields.get('game_hour_progress'),'date':fields.get('date_full')})
    if fields.get('game_speed_notch') not in (1,None) and fields.get('game_speed_index') not in (0,None):
        out['speed_warning']='game is not at 1x; not changing speed'
    Path('research/t173_session_recheck.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'pid':p.pid,'in_game':True,'tag':player.get('tag'),'index':player.get('player_index'),'speed_notch':fields.get('game_speed_notch'),'date':fields.get('date_full'),'speed_warning':out.get('speed_warning')},indent=2))
finally:
    if p is not None: p.close()
