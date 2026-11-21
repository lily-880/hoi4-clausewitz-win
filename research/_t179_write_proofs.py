import json,hashlib
from pathlib import Path
from collections import defaultdict

d=json.loads(Path('research/t179_province_b8_array.json').read_text(encoding='utf-8'))
own=set(d['own'])
# rebuild neighbors from raw buf_head is short; use strides 48 if complete, else reconstruct from 128-byte intent
# The rows have strides['48'] with u32s
graph={}
for r in d['rows']:
    recs=r['strides']['48']
    ids=[]
    for rec in recs:
        u=rec['u32s']
        # expected: [0,0,id,0,flags,619,coord,0,x,y,...]
        if len(u)>=3:
            nid=u[2]
            ids.append(nid)
    graph[r['province_id']]=ids

pairs=[(p,n) for p,ns in graph.items() for n in ns]
internal=[(p,n) for p,n in pairs if n in own]
recip=sum(p in graph.get(n,[]) for p,n in internal)
plausible=sum(1<=n<=20000 for _,n in pairs)
print('stride48 graph',graph)
print('edges',len(pairs),'plausible',plausible,'internal',len(internal),'reciprocal',recip,'self',sum(p in ns for p,ns in graph.items()))

# also check if every record has u[0]==0 and u[1]==0 and u[5]==619
shape_ok=True
notes=[]
for r in d['rows']:
    for rec in r['strides']['48']:
        u=rec['u32s']
        if not (len(u)>=6 and u[0]==0 and u[1]==0 and 1<=u[2]<=20000):
            shape_ok=False
            notes.append((r['province_id'],u[:6]))
print('shape_ok',shape_ok,'bad',notes[:8])

Path('research/t179_adjacency_stride48_empirical.json').write_text(json.dumps({
    'status':'empirical_stride_48_target_plus8_not_promoted',
    'location':'CProvince+0xb8 object, pdx array at +0x70',
    'stride_bytes':48,
    'target_offset':8,
    'graph': {str(k):v for k,v in graph.items()},
    'edges':len(pairs),'plausible_ids':plausible,'internal_own_edges':len(internal),
    'reciprocal_own_edges':recip,
    'self_edges':sum(p in ns for p,ns in graph.items()),
    'shape_records_start_0_0_id':shape_ok,
    'caveat':'Stride 48 is an empirical fit to the live buffer (t156 stride 40 was wrong). Land-vs-sea/strait/river and a code reader of this array are not yet bound. Do not emit as world.provinces.neighbors.'
},indent=2,ensure_ascii=False),encoding='utf-8')

# formulas
formulas={
    'need':{
        'unit_remaining':'For a selected fielded unit, request need equals CReferencedDivisionTemplate+0x120 minus CArmy+0x348 (archetype deficit). t170: unit 1835 template 588 need 400, on-hand 320, remaining 80.',
        'official_country_1409810':'1409810(this,out,type)= cap(1409890(...) + 14080c0(...), [0xffffac1d29df04c0, 0x53e2d620fb40]). 1409890 sums deployment F70+0x60 deficits, reinforcement (request+0x78 need minus request+0x38 produced), then occupation/logistics/operations adders. 14080c0 is CCountryResources+0x758, not request deficits.',
        'this_scene':'deployment/resources/occupation/logistics/operations empty for infantry; only live request is unit 1835 with need 80 produced 3, official 1409810 infantry = 77. Fielded deficit sum 2520 is not this official total.'
    },
    'produced':{
        'accept_path':'Only bound CReinforcementStatus slot 2 accept with a live status and stock r9 is deployment.daily (1eae60 -> 72f220 -> d71810 -> d71b60 @ 0xd723b6). Hourly path is request+logistics, not accept (t178).',
        'formula':'Pre-daily, for each production+0x200 present type with qty>0: offered starts as that FIXED qty; acceptors with slot1 want>0 (resources, occupation, upgrades, deployment lists, then reinforcement) each get slot2(..., r9=offered) and write back the remainder. For non-air reinforcement, cb8e80 passes r9 through; give = min(max(0, need - produced), offered).',
        'not':'produced = min(need, current stock) after the type has left the pool. Live infantry_equipment is absent at hour 12; produced=3 remains t170/t171 evidence.'
    },
    'not_promoted':{
        'demanded':'77 is the reimplemented official 1409810 infantry sum this scene, but no campaign-stored non-UI copy was found.',
        'deficit':'not independently stored or contracted',
        'affected_unit_ids':'Official 1409810 contributors this scene are [1835] (the only live request). 19 fielded units are short. The contract may mean all shortage-affected units; do not promote [1835] as affected_unit_ids.'
    }
}
Path('research/t179_need_produced_formulas.json').write_text(json.dumps(formulas,indent=2,ensure_ascii=False),encoding='utf-8')

# 1409810 store conclusion
callers=json.loads(Path('research/t179_1409810_callers.json').read_text(encoding='utf-8'))
funcs=callers['e8']['1409810']['funcs']
classification={
    '0x2d5b40':'convoy UI strings; result formatted via 2572ef0/254d0a0',
    '0x52df40':'script/event ForEach over country (Infinite cycle in event FROM scope; Parallel ForEach). lock add accumulates (stock-need)/FIXED into a script dword, not a country status field',
    '0x1453780':'IsTradable(...) trade path; result used transiently',
    '0x1ddf4e0':'PRODUCTION_EFFICIENCY UI',
    '0x1de0d60':'PRODUCTION_NAVAL_DEPLOYMENT / total_need UI',
    '0x1df0130':'PRODUCTION_EQUIPMENT_TOTAL_NEED UI',
    '0x1df0810':'PRODUCTION_EQUIPMENT_TOTAL_NEED UI widget flag',
    '0x1e1f6a0':'already-known logistics UI; stores result at UI object +0x648',
    '0x1e208f0':'LOGISTICS_EQUIPMENT_VALUE UI; add to UI object +0x668',
    '0x1fa1a50':'DIPLOMACY_LEND_LEASE_IN_STOCK_VALUE UI'
}
# 140ba10
postdaily={
    'func':'0x140ba10',
    'string':'logistics.postdailythreaded',
    'behavior':'calls 1409630, 1409890, 14080c0; caps the 1409890+14080c0 sum; subtracts from stock; 15b1d90 then 15b3220(type+0x598, difference). Writes a logistics dense-array balance, not a stored official 77.',
    'live_logistics_e48_is_80_not_77':True
}
Path('research/t179_1409810_no_stored_total.json').write_text(json.dumps({
    'e8_count':callers['e8']['1409810']['count'],
    'funcs':funcs,
    'classification':classification,
    'all_ui_or_script_or_known_ui_cache':True,
    'logistics_postdailythreaded':postdaily,
    'bounded_status_scan':'research/t179_bounded_77_scan.json; no i64 77 and no 77*100000 in country and known status objects / production present rows / request objects',
    'logistics_plus_e48':'i64 80 only (1835 request need), not 77',
    'conclusion':'No campaign-stored non-UI official 1409810 total found. Stop this shortage trail this batch.'
},indent=2,ensure_ascii=False),encoding='utf-8')

# offsets
off=Path('calling/tables/offsets_input_windows_1.19.5.json')
a=json.loads(off.read_text(encoding='utf-8-sig'))
a['need_produced_formulas_t179']={
    'unit_need':'template+0x120 minus CArmy+0x348',
    'official_1409810':'1409890 + 14080c0, capped',
    'produced_prediction':'pre-daily remaining share of production+0x200 after earlier acceptors; give=min(max(0,need-produced),offered)',
    'no_stored_official_77':True,
    'proof':'research/t179_need_produced_formulas.json'
}
a['province_adjacency_array_t179']={
    'location':'CProvince+0xb8, pdx array +0x70',
    'empirical_stride':48,
    'empirical_target_offset':8,
    'promoted':False,
    'reason':'stride is empirical; land/sea/river not code-bound',
    'proof':'research/t179_adjacency_stride48_empirical.json'
}
off.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# document hash
doc=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md')
digest=hashlib.sha256(doc.read_bytes()).hexdigest()
expected='4d9f3b10ec11d1bb2fa3448abb74eb8dd27dd4f1f078eb84e609bcdc29b8b24f'
rows=[[c.strip() for c in l.split('|')[1:-1]] for l in doc.read_text(encoding='utf-8').splitlines() if l.strip()]
counts={k:sum(r[1]==k for r in rows) for k in ('已验证','未验证')}
assert digest==expected and counts=={'已验证':41,'未验证':75}
assert sum(r[0]=='字段名' for r in rows)==14
assert len([r for r in rows if r[1] in ('已验证','未验证')])==116
Path('research/t179_document_update_verification.json').write_text(json.dumps({
    'path':str(doc),'sha256':digest,'encoding':'UTF8','tables':14,'columns':3,'fields':116,'counts':counts,
    'promoted_fields':{},
    'unchanged_reason':'no stored official 77; affected_unit_ids contract still ambiguous; adjacency stride 48 is empirical only; formulas recorded in research, not as promoted demanded'
},ensure_ascii=False,indent=2),encoding='utf-8')
Path('research/t179_validation_summary.json').write_text(json.dumps({
    'pid':26976,'hour_tick':60759371,'complete_input':False,'verified':41,'unverified':75,
    'document_sha256':digest,'document_unchanged':True,'promoted_fields':[],
    'stored_77_found':False,'formulas_recorded':True,'adjacency_promoted':False,
    'capture_unchanged':'t171 captures still apply'
},ensure_ascii=False,indent=2),encoding='utf-8')
print('ok',digest,counts,'recip',recip,len(internal))
