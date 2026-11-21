import json,hashlib,collections
from pathlib import Path
from datetime import datetime,timezone,timedelta
root=Path('.');cap=json.loads((root/'research/t156_live_capture.json').read_text(encoding='utf-8'));repeat=json.loads((root/'research/t156_live_capture_repeat.json').read_text(encoding='utf-8'));sv=json.loads((root/'research/t156_schema_validation.json').read_text(encoding='utf-8'))
summary={
 'recorded_at':datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5),'EST')).isoformat(),
 'timezone':'America/New_York (EST)','pid':cap['pid'],'version':cap['game_version'],'sha256':cap['exe_sha256'],
 'capture_time':cap['captured_at'],'game_time':cap['observation']['meta']['game_time'],'current_player_index':44,
 'country_tag':'not emitted; previous helper maps 44 to ETH but new active-mod table not independently verified',
 'observations_equal_across_final_two_runs':cap['observation']==repeat['observation'],
 'units':len(cap['observation']['world']['own_units']),'provinces':len(cap['observation']['world']['provinces']),
 'templates':cap['evidence']['template_handle_registry_checks'],'registered_controlled_and_owned_provinces':cap['evidence']['registered_self_provinces'],
 'speed':'UI setting 1x, observed clock stable; official pause flag unresolved, no speed field emitted',
 'newly_accepted_fields':['Unit.template.template_id','Unit.template.battalions (non-null main battalions)','Province.terrain (loaded engine definition)','Province.controller (registered self country only)','Province.owner (registered self country only)'],
 'reverified_existing':['unit id/handle/class','unit name','province id cross-check','owner index / self relation only','organization','max HP against loaded battalions (21/21)','opening org against 95% loaded mean org (21/21)','equipment ratio opening sample','direct unit officer id'],
 'invalidated_baseline':['1.19.4 fingerprint no longer current','CArmy vtable moved 0x29D6D68 -> 0x29D6D98','GS human flag pair changed from (1,1) to (1,0)','CA+4F0 sometimes 100, not a reliable manpower read','template legacy army handle resolver returns object-0x10; typed correction verified against all 5 country templates'],
 'unproven':['current manpower versus maximum','current HP','supply','in_combat','order semantics','official pause flag','combat_width','non-self relations and visibility','army/army group instances and leadership skills/traits','player-drawn plans versus 6 auto CFront border objects','infrastructure and fort levels','victory points','land adjacency / rivers / passability','war relation states and shortages','feedback ledger'],
 'adjacency_research':{'own_provinces':34,'candidate_stride':48,'candidate_target_offset':8,'candidate_total_edges':203,'internal_edges':154,'internal_reciprocal':154,'accepted':False,'reason':'layout reciprocity only; no independent land/strait/river/passability acceptance'},
 'schema_validation':{'schema':'calling/tables/generalissimo_input.schema.json','valid':sv['valid'],'errors':sv['error_count'],'error_path_counts':dict(collections.Counter(e['path'].split('.')[0] for e in sv['errors'])),'comment':'Full-snapshot shape, not cadence-delta transport or semantic completeness. has_river_crossing edge-map shape unspecified in original Canvas.'},
 'tests':{'passed':21,'synthetic_and_saved_live_fixture_tests':True,'live_capture_runs_final':2,'compilation_passed':True},
 'table':{'path':'research/态势信息读取能力清单_1.19.5修订.md','tables':14,'rows':119,'verified_rows':18,'format':'three columns only','original_D_document_changed':False,'note':'Rebuilt from Canvas input contract, not an exact in-place diff against inaccessible old 116 rows.'},
 'restrictions_observed':['read-only process access','no memory write/Post/injection','no speed/pause changes','no save reading/writing','no game restart/new game','no commit or push','existing user dirty files untouched'],
 'access_limits':['Original D-drive document refused on previous turn; no bypass or update attempted.','Static common/units/infantry.txt Read refused by allowed-root policy this turn; no Shell fallback attempted for that file.','Terrain/battalion data therefore taken directly from live loaded definitions, not static base files.'],
 'next_minimum_conditions':[
  {'need':'current manpower/HP/in_combat/combat structure','condition':'a known division with battle damage and a known active battle, plus UI values for independent comparison','operations_not_yet_authorized_or_done':'on disposable test only, enter one battle at 1x, pause at a damaged state; current campaign untouched'},
  {'need':'order/path/ETA','condition':'known unit with an accepted nonempty movement path, then optionally strategic redeploy and retreat contrasts','operations_not_yet_authorized_or_done':'issue test movement only after permission in disposable test'},
  {'need':'supply','condition':'known supplied versus starved/isolated unit, with independent UI tooltip comparison','operations_not_yet_authorized_or_done':'provide existing contrasting state or authorize isolated test scenario'},
  {'need':'formation/leader/plan fields','condition':'one army, one army group, assigned general and nonempty drawn frontline/offensive order','operations_not_yet_authorized_or_done':'create these only in approved disposable test or let user prepare'},
  {'need':'visibility','condition':'one independently known visible enemy and one hidden enemy without including hidden data in exported visible_units','operations_not_yet_authorized_or_done':'no fog bypass or hidden unit export'},
  {'need':'static independent map/unit confirmation or original table update','condition':'sanctioned local-tool permission for exact paths, or user-provided copies inside allowed workspace','operations_not_yet_authorized_or_done':'no alternate route around allowed-root refusal'}],
 'complete_input':False}
files=['calling/input_observation.py','calling/input_capture_live.py','calling/tables/offsets_input_windows_1.19.5.json','calling/tables/generalissimo_input.schema.json','research/t156_live_capture.json','research/t156_live_capture_repeat.json','research/t156_schema_validation.json','research/态势信息读取能力清单_1.19.5修订.md']
summary['artifact_sha256']={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
(root/'research/t156_input_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:summary[k] for k in ('recorded_at','observations_equal_across_final_two_runs','units','provinces','templates','complete_input')},ensure_ascii=False,indent=2))
