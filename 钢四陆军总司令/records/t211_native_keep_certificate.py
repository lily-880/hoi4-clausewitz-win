"""t211 narrow offline proof for the captured Windows native branches only.
Not a production collector. No live backend import, writes, native calls, or ended phase.
Inputs are exact saved process observations, including independent identity/slot checks.
"""
import json
from pathlib import Path

NAMES = ['t211_current_battle_end_condition_inputs.json',
         't211_relationship_subobject_type_diagnostic.json',
         't211_keep_identity_and_binding_certificate.json',
         't211_phase_manager_handle_diagnostic.json']

def load(root):
    return [json.loads((Path(root)/n).read_text(encoding='utf-8')) for n in NAMES]

def ongoing(data, ptr):
    try:
        raw, rel, binding, manager = data
        guard = raw['guard']
        if any(x['guard'] != guard for x in data): return None
        if guard['pause'] != 1 or guard['speed_slot'] != 0: return None
        if raw['defines'] != {'time_threshold_i32':4, 'side_average_threshold_i64':100000}: return None
        c = next(x for x in raw['combats'] if x['ptr']==ptr)
        m = next(x for x in manager['rows'] if x['ptr']==ptr)
        ids = binding['correct_ids'][ptr]
        if not m['active_manager_member'] or m['combat_handle_type']!=62: return None
        if m['current_combat_id'] != ids['combat_id'] or not ids['own_army_ids']: return None
        if any(x['handle_type']!=51 for x in m['side_handles']): return None
        if binding['combat_slots'][ptr] != {'72':0x1348e10,'88':0x2b3e00,'96':0x133e5d0,'128':0x1348d30}: return None
        if c['flags_51_52'] != [1,0] or c['clock44']<4: return None
        if len(c['sides'])!=2: return None
        tags=[s['countrytags'] for s in c['sides']]
        if any(not t or len(t)!=len(set(t)) for t in tags): return None
        def relationship(a,b):
            if a==b: return False  # exact native 74841a/74841c branch, not a sampled zero
            row=next(x for x in rel['rows'] if x['source']==a and x['target']==b)
            if row['diplomacy_class']!='.?AVCDiplomacyStatus@@' or row['relation_class']!='.?AVCRelationStatus@@' or row['subobject_class']!='.?AVCWarRelation@@': raise ValueError('unbound relation type')
            if row['subobject_vtable']!='0x29dcc08' or not 0<row['source_index']<2048 or not 0<row['target_index']<2048: raise ValueError('unbound relation index/type')
            if row['source_index']==row['target_index']: return False
            return row['flag49']==0
        for i in (0,1):
            for t in tags[i]:
                if any(relationship(t,x) for x in tags[i]): return None
                if not any(relationship(t,x) for x in tags[1-i]): return None
        sums=[]
        for side in c['sides']:
            if side['flagD9']!=0: return None
            if binding['side_slots'][side['ptr']] != {'160':0x147fe20,'200':0x1347b80,'224':0x147e440}: return None
            rows=side['members']; units={u['ptr']:u for u in rows}
            if len(rows)!=len(units): return None
            all_units=[u for u in rows if u['in_all']]
            front=side['frontline']; reserve=side['reserve']; selected=front+reserve
            if not all_units or not front or len(selected)!=len(set(selected)) or len(selected)>2048: return None
            if any(p not in units for p in selected): return None
            for u in rows:
                if binding['unit_bindings'][u['ptr']]['slots'] != {'248':0xce4d70,'288':0xce4d60,'296':0xcd9a10}: return None
                if not 0<=u['raw420']<=(2**63-1)//(100000*2048) or not 0<=u['raw428']<=(2**63-1)//(100000*2048): return None
            total=sum(u['raw420'] for u in all_units)
            orgsum=sum(units[p]['raw428'] for p in selected)
            # Positive bounded operands: no native sentinel or signed-IMUL overflow;
            # exact imul100000 / (count*100000) with truncation toward zero.
            average=(orgsum*100000)//(len(selected)*100000)
            if total<1000 or average<=100000: return None
            sums.append({'total_raw420':total,'average_raw428':average,'native_side_end':False})
        return {'combat_id':ids['combat_id'],'phase':'ongoing','native_side_certificates':sums}
    except (KeyError,TypeError,ValueError,StopIteration,OverflowError):
        return None
