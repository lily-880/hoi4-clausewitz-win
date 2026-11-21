"""Materialize full-snapshot INPUT shape from the frozen Canvas contract.
Not the delta/dirty-event transport schema, nor a semantic-proof validator.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def obj(props,required=()):return {'type':'object','properties':props,'required':list(required),'additionalProperties':False}
def arr(t):return {'type':'array','items':t}
def ref(n):return {'$ref':'#/$defs/'+n}
def enum(*values):return {'enum':list(values)}
I={'type':'integer'};N={'type':'number'};S={'type':'string'};B={'type':'boolean'}
R={'type':'number','minimum':0,'maximum':1}
IDS=arr(I)
D={}
D['CountryRef']=obj({'index':I,'tag':S},['index'])
D['GameTime']=obj({'year':I,'month':{'type':'integer','minimum':1,'maximum':12},'day':{'type':'integer','minimum':1,'maximum':31},'hour':{'type':'integer','minimum':0,'maximum':24}},['year','month','day','hour'])
D['OrderType']=enum('idle','move','strategic_redeploy','attack','support_attack','retreat','garrison','training','exercise','unknown')
D['Relation']=enum('self','ally','enemy','neutral','subject','overlord','unknown')
D['Template']=obj({'template_id':I,'name':S,'battalions':arr(obj({'type':S,'count':I},['type','count'])),'combat_width':N},['template_id'])
D['Strength']=obj({'manpower':I,'current':N,'max':N,'equipment_ratio':R})
D['Supply']=obj({'in_supply':B,'ratio':N,'isolated':B},['in_supply'])
D['Order']=obj({'type':ref('OrderType'),'target_province_ids':IDS,'path_province_ids':IDS,'eta':obj({'hours':N,'progress':N})},['type','target_province_ids','path_province_ids'])
D['Formation']=obj({'army_id':I,'army_group_id':I})
D['Unit']=obj({'unit_id':I,'name':S,'province_id':I,'owner':ref('CountryRef'),'relation_to_player':ref('Relation'),
 'template':ref('Template'),'organization':N,'strength':ref('Strength'),'supply':ref('Supply'),'in_combat':B,'combat_id':I,'order':ref('Order'),'formation':ref('Formation'),'leader_id':I},
 ['unit_id','province_id','owner','relation_to_player','in_combat','order'])
D['VisibleUnit']=json.loads(json.dumps(D['Unit']));D['VisibleUnit']['properties']['visibility']=obj({'spotted':B,'confidence':R},['spotted']);D['VisibleUnit']['required'].append('visibility')
D['ArmyGroup']=obj({'army_group_id':I,'name':S,'leader_id':I,'army_ids':IDS},['army_group_id','army_ids'])
D['Army']=obj({'army_id':I,'name':S,'leader_id':I,'unit_ids':IDS,'plan_id':I},['army_id','unit_ids'])
D['Leader']=obj({'leader_id':I,'name':S,'skill':N,'attack':N,'defense':N,'planning':N,'logistics':N,'traits':arr(S),'assigned_to':obj({'kind':enum('army','army_group','unit'),'id':I},['kind','id'])},['leader_id'])
D['Province']=obj({'province_id':I,'controller':ref('CountryRef'),'owner':ref('CountryRef'),'terrain':S,'infrastructure':I,'fort_level':I,'coastal_fort_level':I,'victory_points':obj({'value':N,'name':S},['value']),'neighbors':IDS,
 'has_river_crossing':{'anyOf':[B,{'type':'object'}]}},['province_id','terrain','infrastructure','fort_level'])
D['Plan']=obj({'plan_id':I,'type':enum('frontline','offensive_line','garrison','area_defense'),'vertex_province_ids':IDS,'assigned_army_ids':IDS,'assigned_unit_ids':IDS,'executing':B,'axis_province_ids':IDS,'status':enum('ok','blocked','stalled','invalid')},['plan_id','type','vertex_province_ids','assigned_army_ids','assigned_unit_ids','executing'])
D['Combat']=obj({'combat_id':I,'province_id':I,'attacker_unit_ids':IDS,'defender_unit_ids':IDS,'phase':enum('ongoing','ended'),'result':enum('our_victory','our_defeat','inconclusive'),
 'casualties':obj({'our_manpower':I,'enemy_manpower':I,'our_org_loss':N,'enemy_org_loss':N}),'started_at':ref('GameTime'),'ended_at':ref('GameTime')},['combat_id','province_id','attacker_unit_ids','defender_unit_ids','phase'])
D['Crisis']=obj({'kind':enum('encircled','encirclement_imminent','org_collapse','out_of_supply','plan_failed'),'unit_ids':IDS,'province_ids':IDS,'severity':enum('watch','high','critical'),'notes':S},['kind','unit_ids','province_ids','severity'])
D['War']=obj({'a':ref('CountryRef'),'b':ref('CountryRef'),'state':enum('at_war','ceasefire','capitulated','puppeted','not_at_war'),'front_invalidated':B},['a','b','state'])
D['Shortages']=obj({'equipment':arr(obj({'equipment_type':S,'stockpile':I,'demanded':I,'deficit':I,'affected_unit_ids':IDS,'affected_plan_ids':IDS},['equipment_type'])),
 'manpower':obj({'available':I,'needed':I,'deficit':I,'affected_unit_ids':IDS,'front_cannot_hold':B}),
 'missing_divisions':obj({'plan_id':I,'province_ids':IDS,'needed_estimate':I,'reason':S},['reason'])},['equipment','manpower'])
plan_commands=['create_frontline','create_offensive_line','create_garrison','assign_to_plan','reassign_unit','create_army','create_army_group','assign_leader','use_leader_ability','train','exercise']
D['Feedback']=obj({'last_orders':arr(obj({'order_seq':I,'type':{'anyOf':[ref('OrderType'),enum(*plan_commands)]},'subject_ids':IDS,'target_province_ids':IDS,'plan_id':I,'accepted':B,'error':S},['order_seq','type','subject_ids','accepted'])),'ticks_since_issue':I},['last_orders'])
world={key:arr(ref(t)) for key,t in [('own_units','Unit'),('visible_units','VisibleUnit'),('army_groups','ArmyGroup'),('armies','Army'),('leaders','Leader'),('provinces','Province'),('plans','Plan'),('combats','Combat'),('crises','Crisis'),('wars','War')]}
world['shortages']=ref('Shortages')
schema=obj({'meta':obj({'game_time':ref('GameTime'),'player_country':ref('CountryRef'),'speed':enum('pause','1x'),'allow_write':B,
 'geography_scope':{'anyOf':[{'type':'null'},obj({'kind':enum('global')},['kind']),obj({'kind':enum('theater'),'province_ids':IDS},['kind','province_ids'])]}}),
 'policy':obj({'stance':enum('preserve_force','hold_line','annihilate','economize_manpower','custom'),'instructions':S}),
 'world':obj(world,list(world)),'feedback':ref('Feedback')},['meta','policy','world','feedback'])
schema['properties']['meta']['required']=['game_time','player_country','speed','allow_write','geography_scope']
schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$defs':D,
 'title':'GeneralissimoInput full snapshot shape (not delta transport)',
 '$comment':'Transcribed from Canvas 4688f13e-df44-4e3f-a501-69afa305b270. Shape validity is not semantic proof. Policy fields may be omitted for documented defaults; cadence delta messages need a separate merge validator. has_river_crossing edge mapping is left object-shaped because the source has no canonical edge schema.'})
out=ROOT/'calling/tables/generalissimo_input.schema.json';out.write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf-8')
from jsonschema import Draft202012Validator
Draft202012Validator.check_schema(schema)
cap=json.loads((ROOT/'research/t156_live_capture.json').read_text(encoding='utf-8'))
errors=sorted(Draft202012Validator(schema).iter_errors(cap['observation']),key=lambda e:str(list(e.path))+e.message)
report={'kind':'full_snapshot_shape_validation','valid':not errors,'semantic_complete':False,'source_capture':'research/t156_live_capture.json',
 'error_count':len(errors),'errors':[{'path':'.'.join(map(str,e.path)),'message':e.message} for e in errors]}
(ROOT/'research/t156_schema_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'schema':str(out),'live_partial_valid':not errors,'error_count':len(errors)}))
