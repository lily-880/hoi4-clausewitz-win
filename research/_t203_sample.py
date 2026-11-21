from _t203_common import *
from _t203_delivery_reader import delivery_possible
from input_observation import ObservationError
x=Runtime()
try:
 before=x.guard();r=x.reader();out={'own':[],'existing_enemy_combatants':[],'errors':[]};own=set(r.array(x.country+0x290,2048));others=set()
 for cp in r.array(x.gs+0x268,4096):
  for off in(0x28,0x30):others.update(r.array(r.q(cp+off)+0xe8,128))
 for label,group in(('own',own),('existing_enemy_combatants',others-own)):
  for ap in sorted(group):
   try:v,ev=delivery_possible(r,x.gs,ap);out[label].append({'unit_id':r.i(ap+0x1c),'delivery_possible':v,'isolated_candidate':not v,'evidence':ev})
   except(AssertionError,ObservationError)as e:out['errors'].append({'unit_id':r.i(ap+0x1c),'error':str(e)})
 r.stable();out['guard_after']=x.guard();assert before==out['guard_after'];out['schema_emission']=False;(R/'research/t203_delivery_live_candidate.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:x.close()
