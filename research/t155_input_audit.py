"""Offline re-audit of existing evidence only. Never attach to the game."""
import copy
import hashlib
import importlib.util
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('observation',ROOT/'calling/input_observation.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def load(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
old=load('research/_t143_own_units.json')
proof=load('research/_t144_probe4.json')
rows=proof['verify']
by_id={r['id']:r for r in rows}
assert len(rows)==len(by_id)==21
assert all(all(r[k] is True for k in ('org_ok','hp_ok','eq_ok','xp_ok')) for r in rows)
assert {u['unit_id'] for u in old['world']['own_units']}==set(by_id)
units=[]
for original in old['world']['own_units']:
    u={k:copy.deepcopy(original[k]) for k in ('unit_id','name','province_id','owner') if k in original}
    assert u['owner']['index']==old['meta']['player_country']['index']
    u['relation_to_player']='self'
    r=by_id[u['unit_id']]
    u['organization']=r['org']
    u['strength']={'max':r['hp'],'equipment_ratio':r['eq1']}
    units.append(u)
partial={'meta':{k:copy.deepcopy(old['meta'][k]) for k in ('game_time','player_country')},'world':{'own_units':units}}
# Do NOT manufacture speed, feedback, unseen world collections, current manpower,
# in_combat, idle orders, template IDs, or a live capture timestamp.
blockers=[{'unit_id':u['unit_id'],'errors':m.unit_blockers(u)} for u in units]
assert all(len(row['errors'])==2 for row in blockers)
sources=[]
for name in ('research/_t143_own_units.json','research/_t144_probe4.json','research/_t144_probe5.json','research/_t144_fields.json'):
    sources.append({'path':name,'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()})
report={
 'audited_at':datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5),'EST')).isoformat(),
 'time_zone':'America/New_York (EST)',
 'mode':'offline_existing_evidence_only','live_fields_newly_verified':[],
 'complete_input':False,'full_schema_validated':False,
 'environment':{'process_check':'Get-Process filter hoi|heart returned 0 matches',
  'target_machine':'a849f760-4114-424f-af9c-d10eef8ca3e8',
  'game_started_or_modified':False,
  'document_read':'refused: outside allowed local-exec root; no alternative route attempted',
  'static_map_check':'not attempted: game not running; active mod/map identity not established'},
 'historical_recheck':{'unit_count':21,'organization_matches':21,'max_hp_matches':21,'equipment_matches':21,'experience_matches':21,
  'caveat':'Recomputed assertions from previous evidence; not independent live verification.'},
 'corrections':[
  {'field':'strength.manpower','status':'unverified','reason':'4F0 matches full template manpower only; current versus max unresolved'},
  {'field':'relation_to_player','status':'self_only','reason':'same owner index proves self; no ally/enemy/subject relation resolver'},
  {'field':'meta.allow_write','status':'configuration_not_memory','default':False},
  {'field':'meta.geography_scope','status':'configuration_not_memory','default':None},
  {'field':'policy','status':'configuration_not_memory','reason':'player instructions or documented default, not engine discovery'},
  {'field':'meta.speed','status':'unverified_official_pause','reason':'4BC is setting only; a frozen sample does not prove pause'},
  {'field':'order.path_province_ids','status':'empty_example_only','reason':'no proof of nonempty path serialization'},
  {'field':'template','status':'required_template_id_unresolved','reason':'name-only nested object is not a valid complete template'},
  {'field':'in_combat/order','status':'required_and_missing','reason':'unit observation cannot be called complete Input'},
  {'field':'supply/current_HP/visibility','status':'unverified','reason':'no positive semantic/live contrast proof'}],
 'sources':sources,'historical_partial_observation':partial,
 'unit_necessary_shape_blockers':blockers,
 'other_blockers':['meta.speed absent','policy/feedback not collected','other world domains not collected','no full schema validator','no live capture or active-mod/version fingerprint'],
 'implementation':{'module':'calling/input_observation.py','status':'implemented and synthetic-tested; not live-accepted',
  'functions':['observe_own_divisions(read, country_ptr, player_index, carmy_vtable=..., version_verified=...)','unit_blockers(unit)'],
  'limits':['no process attachment or automatic resolver','caller must independently verify executable version and fresh context','4096 row bound','no write methods','not full-schema validation','no atomic scalar snapshot']},
 'next_conditions':[
  'User starts HOI4 and loads a disposable test campaign manually, paused or 1x; do not exit/change the current session automatically.',
  'Grant sanctioned local-exec access to the requested D-drive folder before reading/updating its original 116-row table.',
  'First reverify executable fingerprint, active mods, GS/player and current arrays without issuing orders.',
  'If nonempty states still absent, obtain approval for a disposable test: movement, damage, low supply, army/group, frontline and active battle.',
  'Visibility needs one known-visible and one known-hidden enemy unit without exporting the hidden unit as visible.'
 ]}
output=ROOT/'research/t155_input_audit.json'
output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(output),'mode':report['mode'],'historical_units':len(units),'new_live_fields':0,'unit_required_field_blockers':sum(len(x['errors']) for x in blockers),'complete_input':False},ensure_ascii=False))
