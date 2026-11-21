"""Narrow research candidate, never production schema or remote execution."""
from input_observation import ObservationError

def battle_people_loss_candidate(r,side):
 r.require(side,'CLandCombatant');observer=side+0x1d0;r.require(observer,'CStatsObserver@NCombatLog');count=r.i(observer+0x60)
 if count<0:raise ObservationError('negative/overflowed people counter')
 return {'candidate_people_loss':count,'observer':hex(observer),'schema_emission':False,'positive_live_proof_required':True}
