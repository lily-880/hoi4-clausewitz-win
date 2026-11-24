"""Commander live input: tolerant wrapper around the sealed production capture.

Body copied from calling/input_capture_live.py capture() (sealed file left
untouched). Differences, all recorded in evidence['tolerant_omissions']:
  * a division whose max HP no longer equals the sum of its loaded battalions
    keeps all other readings; only strength.max is omitted;
  * templates with support companies no longer abort the capture; support
    companies are simply not listed in template.battalions.
Consistency checks (anything "changed during capture") still raise; capture()
retries those a few times while the game is paused.
Read-only: no Post, no writes, no save access.
"""
from __future__ import annotations
import hashlib
import json
import os
import struct
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE=Path(__file__).resolve().parent

def _capture_once():
    os.environ['CLAUSEWITZ_ALLOW_POST']='0'
    os.environ['CLAUSEWITZ_ALLOW_WRITE']='0'
    from mem import Proc,find_pid
    from pe import PE
    from gamestate import _rtti_name_from_vtable,_pdx_array,detect_session,resolve_player_country,read_campaign_summary
    from handle import resolve_handle
    from live_observation import observe_own_divisions,unit_blockers
    from input_observation import ObservationError
    from input_loaded_fields import LoadedReader,battalion_width,own_leaders,infrastructure,country_tag,victory_points,unit_current_manpower,country_available_manpower,unit_hp,own_equipment_stockpile,resolve_building_templates,province_fort_level,province_land_neighbors,province_adjacencies,own_reinforcement_requests,official_country_equipment_need_components
    profile=json.loads((HERE/'tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8-sig'))
    p=Proc(find_pid('hoi4.exe'))
    try:
        h=hashlib.sha256()
        with open(p.image_path,'rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        digest=h.hexdigest().upper()
        if digest!=profile['exe_sha256']:
            raise ObservationError('unknown executable fingerprint; no layout reads')
        pe=PE(p.image_path)
        def ptr(x):return type(x) is int and 0x10000<x<0x7fffffffffff
        def q(a):return struct.unpack('<Q',p.read(a,8))[0]
        def i(a):return struct.unpack('<i',p.read(a,4))[0]
        def cls(a):
            if not ptr(a):return None
            vt=q(a)
            if not p.base<=vt<p.base+p.image_size:return None
            return _rtti_name_from_vtable(pe,vt-p.base)
        def require_class(a,name):
            if cls(a) not in ('.?AV'+name+'@@','.?AU'+name+'@@'):
                raise ObservationError('unexpected '+name+' RTTI')
        def string(a):
            blob=p.read(a,32);size,cap=struct.unpack_from('<QQ',blob,16)
            if not 0<=size<=1024 or cap<size:raise ObservationError('invalid string header')
            data=blob[:size] if cap<=15 else p.read(struct.unpack_from('<Q',blob)[0],size)
            s=data.decode('utf-8')
            if not all(c.isprintable() for c in s):raise ObservationError('nonprintable name')
            return s
        def array(a,bound):
            ar=_pdx_array(p,a)
            if not ar or not 0<=ar['size']<=ar['capacity']<=max(bound,100):
                raise ObservationError('invalid bounded array')
            if ar['size']>bound or (ar['size'] and not ptr(ar['data'])):
                raise ObservationError('array bound/data invalid')
            return ar,[q(ar['data']+8*j) for j in range(ar['size'])]
        gs=q(p.base+profile['globals']['G_GAMESTATE'])
        require_class(gs,'CCurrentGameState')
        session=detect_session(p,pe)
        if not session['in_game']:raise ObservationError('not in campaign map')
        res=resolve_player_country(p,gs)
        if not res['ok'] or not res['source'].startswith('gs_0x520'):
            raise ObservationError('current player unresolved')
        co=int(res['country_ptr'],16);require_class(co,'CCountry')
        speed=i(gs+0x4bc)
        if speed!=0:raise ObservationError('speed setting not 1x; not changed')
        idler = int(session['signals']['idler_ptr'], 16)
        require_class(idler, 'CInGameIdler')
        official_pause = p.read(idler + 0x6c1, 1)
        if official_pause not in (b'\0', b'\1'):
            raise ObservationError('invalid official pause flag')
        header=p.read(gs+0x468,0xc0)
        kw=dict(country_ptr=co,player_index=res['player_index'],
                carmy_vtable=p.base+profile['vtable_rvas']['CArmy'],
                version_verified=True,strength420_semantics='current',layout_label='Windows HOI4 '+profile['game_version'])
        first=observe_own_divisions(p.read,**kw)
        second=observe_own_divisions(p.read,**kw)
        if first['world']!=second['world']:raise ObservationError('division scalar observations changed; retry later')
        ar,army_ptrs=array(co+0x290,4096)
        if len(army_ptrs)!=len(first['world']['own_units']):raise ObservationError('division membership changed')
        template_cache={};province_cache={};extra=[];template_notes={};transit_units=[]
        loaded=LoadedReader(p.read,cls);infrastructure_evidence=[];neighbor_evidence=[]
        live_tag=country_tag(loaded,gs,res['player_index'],co)
        manpower_available,manpower_available_evidence=country_available_manpower(loaded,co,res['player_index'])
        equipment_stockpile,equipment_stockpile_evidence=own_equipment_stockpile(loaded,co)
        # Request collector needs army identities; filled after the own-army array is read.
        building_templates,building_definition_evidence=resolve_building_templates(loaded,p.base)
        fort_evidence=[]
        manpower_evidence=[];hp_evidence=[]
        leaders,leader_evidence=own_leaders(loaded,co)
        # Restricted proof: only regions explicitly registered to this country.
        # No inference of controller/owner from a division's nationality.
        area_memberships={};area_headers=[];area_lists=[]
        for field,offset,area_class,province_field in (
            ('controller',0x548,'CControllerArea',0xd0),
            ('owner',0x560,'COwnerArea',0xd8)):
            country_area_header=p.read(co+offset,16)
            _,areas=array(co+offset,100)
            area_lists.append((co+offset,100,areas))
            membership={}
            for area in areas:
                require_class(area,area_class)
                member_header=p.read(area+0x30,16)
                _,members=array(area+0x30,2000)
                area_lists.append((area+0x30,2000,members))
                for province in members:
                    require_class(province,'CProvince')
                    if q(province+province_field)!=area:
                        raise ObservationError('province area reverse pointer mismatch')
                    if province in membership:raise ObservationError('duplicate area membership')
                    membership[province]=area
                area_headers.append((area+0x30,member_header))
            area_headers.append((co+offset,country_area_header))
            area_memberships[field]=membership
        class Adapter:
            image_base=p.base
            def read(self,a,n):return p.read(a,n)
        for u,ap in zip(first['world']['own_units'],army_ptrs):
            if p.u32(ap+0x1c)!=u['unit_id']:raise ObservationError('division slot changed')
            u['owner']['tag']=live_tag
            current_manpower,mp_evidence=unit_current_manpower(loaded,ap)
            u['strength']['manpower']=current_manpower
            try:
                hp_current,hp_max,hpe=unit_hp(loaded,ap)
            except ObservationError as e:
                # Tolerant: keep the division, omit only max HP (recorded below).
                hp_current,hp_max,hpe=u['strength']['current'],None,{'omitted':str(e)}
            if hp_current!=u['strength']['current']:raise ObservationError('current HP changed')
            if hp_max is not None:
                u['strength']['max']=hp_max
            hp_evidence.append(dict(hpe,unit_id=u['unit_id']))
            manpower_evidence.append(dict(mp_evidence,unit_id=u['unit_id']))
            member=q(ap+0x340);require_class(member,'CNameGroupMember')
            name=string(member+0x60)
            if name:u['name']=name
            tp=q(ap+0x3b8);require_class(tp,'CReferencedDivisionTemplate')
            if tp not in template_cache:
                ty,tid=struct.unpack('<II',p.read(tp+8,8))
                # Legacy army resolver subtracts 0x10; this handle class's raw
                # registry object pointer is the template itself (5/5 tested).
                resolved=resolve_handle(Adapter(),ty,tid,p.base)
                if ty!=0x34 or not resolved or resolved+0x10!=tp:
                    raise ObservationError('template handle registry cross-check failed')
                types=Counter();hp=0;org=[];width=0
                _,slots=array(tp+0x68,25)
                for sp in slots:
                    cn=cls(sp)
                    if cn and 'TNullObject@VCSubUnitDefinition' in cn:continue
                    require_class(sp,'CSubUnitDefinition')
                    typename=string(sp+0x18)
                    if not typename:raise ObservationError('empty battalion name')
                    types[typename]+=1;hp+=struct.unpack('<q',p.read(sp+0x288,8))[0]/100000;org.append(struct.unpack('<q',p.read(sp+0x280,8))[0]/100000)
                    width+=battalion_width(loaded,sp)
                _,supports=array(tp+0x88,5)
                support_note={'supports_present':len(supports),'supports_omitted':bool(supports)}
                item={'template_id':tid,'combat_width':width,'battalions':[{'type':k,'count':v} for k,v in sorted(types.items())]}
                tn=string(tp+0x20)
                if tn:item['name']=tn
                template_cache[tp]=(item,hp,sum(org)/len(org) if org else None)
                template_notes[tid]=support_note
            template,hp,mean_org=template_cache[tp]
            u['template']=template
            extra.append({'unit_id':u['unit_id'],'template_id':template['template_id'],
                          'max_hp_matches_loaded_battalions':('max' in u['strength'] and abs(u['strength']['max']-hp)<0.0001),
                          'opening_org_matches_95pct_mean':mean_org is not None and abs(u['organization']-.95*mean_org)<.0001})
            pp=q(ap+0x1f0);require_class(pp,'CProvince')
            if pp not in province_cache:
                pid=p.u32(pp+0xa4)
                definition=q(pp+0xb8);terrain=q(definition+0xa8)
                require_class(terrain,'CTerrainType')
                terrain_name=string(terrain+0x18)
                if not terrain_name:raise ObservationError('missing terrain name')
                province_cache[pp]={'province_id':pid,'terrain':terrain_name,'victory_points':victory_points(loaded,pp)}
                adj=province_adjacencies(loaded,pp)
                neighbor_evidence.append(adj['evidence'])
                province_cache[pp]['neighbors']=adj['neighbors']
                province_cache[pp]['has_river_crossing']=adj['has_river_crossing']
                for field,type_name in [('fort_level','bunker'),('coastal_fort_level','coastal_bunker')]:
                    level,fe=province_fort_level(loaded,pp,building_templates[type_name])
                    fort_evidence.append(dict(fe,province_id=pid,field=field))
                    if level is not None:province_cache[pp][field]=level
                try:  # tolerant: a province without a state object (null +0xC0) just omits it
                    infra,infra_evidence=infrastructure(loaded,pp,building_templates['infrastructure'])
                    infrastructure_evidence.append(dict(infra_evidence,province_id=pid))
                    if infra is not None:province_cache[pp]['infrastructure']=infra
                except OSError:
                    pass
                for field,membership in area_memberships.items():
                    if pp in membership:
                        province_cache[pp][field]={'index':res['player_index']}
            if province_cache[pp]['province_id']!=u['province_id']:
                transit_units.append(u['unit_id'])  # in transit: +0x1F0 object differs from +0x28
        # Tolerant: a unit whose engine max HP no longer equals the plain sum of
        # its loaded battalions keeps its readings, but strength.max is omitted.
        omitted_max=[]
        for u,e in zip(first['world']['own_units'],extra):
            if not e['max_hp_matches_loaded_battalions']:
                u['strength'].pop('max',None);omitted_max.append(u['unit_id'])
        if p.read(gs+0x468,0xc0)!=header:
            raise ObservationError('clock/player header changed during capture')
        # Recheck pointer membership after all dependent object reads.
        _,end_ptrs=array(co+0x290,4096)
        if army_ptrs!=end_ptrs:raise ObservationError('division membership changed at end')
        for address,original in area_headers:
            if p.read(address,16)!=original:
                raise ObservationError('country/area membership header changed')
        for address,bound,original in area_lists:
            _,current=array(address,bound)
            if current!=original:
                raise ObservationError('area registration/membership changed in place')
        army_ids={ap:u['unit_id'] for u,ap in zip(first['world']['own_units'],army_ptrs)}
        # Tolerant: these feed only equipment-need evidence; a long wartime list
        # (bound 64) must not abort the whole capture.
        try:
            reinforcement_requests,reinforcement_request_evidence=own_reinforcement_requests(loaded,co,army_ids)
        except (ObservationError, OSError) as e:
            reinforcement_requests,reinforcement_request_evidence=[],{'omitted':str(e)}
        try:
            official_need,official_need_evidence=official_country_equipment_need_components(loaded,co,army_ids)
        except (ObservationError, OSError) as e:
            official_need,official_need_evidence={},{'omitted':str(e)}
        from input_loaded_fields import (own_plans, own_active_combats, own_armies,
            own_army_groups, unit_formation_army_id, unit_formation_army_group_id)
        armies, army_evidence = own_armies(loaded, co)
        army_groups, army_group_evidence = own_army_groups(loaded, co)
        from input_loaded_fields import unit_supply
        supply_evidence = {}
        def _edge_progress(ap, next_pid):
            # t209: C51970/C52C90 = raw(CArmy+0x240)*100000 / C52FD0 edge distance;
            # consumers divide by 100000.0. Ordinary land edges only (types 0/2/3),
            # distance = qword at adjacency row+0x18 (stride 0x30, neighbour id +8).
            pp_ = q(ap + 0x1F0); definition = q(pp_ + 0xB8)
            data_, cap_, n_ = struct.unpack('<QII', p.read(definition + 0x70, 16))
            if not (0 < n_ <= cap_ <= 255) or not ptr(data_):
                return None
            raw_rows = p.read(data_, n_ * 0x30)
            for k in range(n_):
                nid, typ = struct.unpack_from('<II', raw_rows, k * 0x30 + 8)
                if nid == next_pid:
                    if typ not in (0, 2, 3):
                        return None
                    dist = struct.unpack_from('<q', raw_rows, k * 0x30 + 0x18)[0]
                    raw = i(ap + 0x240)
                    if dist <= 0 or raw < 0:
                        return None
                    return round(min(raw / dist, 1.0), 4)
            return None
        for unit, up in zip(first['world']['own_units'], army_ptrs):
            unit['supply'], supply_evidence[unit['unit_id']] = unit_supply(loaded, up, p.base)
            army_id, _ = unit_formation_army_id(loaded, up)
            group_id, _ = unit_formation_army_group_id(loaded, up)
            formation = {}
            if army_id is not None:
                formation['army_id'] = army_id
            if group_id is not None:
                formation['army_group_id'] = group_id
            if formation:
                unit['formation'] = formation
            # Current route: CArmy+0x200 ordered u32 provinces (inventory: verified).
            # Type is only named for the verified strategic flag (+0x2AF); any other
            # active route is 'unknown' (an ordinary move and an attack look alike).
            pdata, pcap, psize = struct.unpack('<QII', p.read(up + 0x200, 16))
            route = []
            if 0 < psize <= pcap <= 64 and ptr(pdata):
                route = list(struct.unpack('<' + 'I' * psize, p.read(pdata, psize * 4)))
            if route:
                strategic = p.read(up + 0x2AF, 1)[0] == 1
                unit['order'] = {'type': 'strategic_redeploy' if strategic else 'unknown',
                                 'target_province_ids': [route[-1]],
                                 'path_province_ids': route}
                prog = _edge_progress(up, route[0])
                if prog is not None:
                    unit['order']['eta'] = {'progress': prog}
        plans, plan_evidence = own_plans(loaded, co)
        # Tolerant copy of own_active_combats: the GS active-combat list can also
        # hold non-land combats (naval/air) once other powers join the war; those
        # are skipped instead of aborting the capture.
        def is_land_combat(cp_):
            return loaded.class_name(cp_) in ('.?AVCLandCombat@@', '.?AUCLandCombat@@')
        skipped_non_land = 0
        combats = []
        own_ids_ = {u['unit_id'] for u in first['world']['own_units']}
        for cp in loaded.array(gs + 0x268, 4096):
            if not is_land_combat(cp):
                skipped_non_land += 1
                continue
            sp = cp + 0x10
            sides = {}
            for name, off in (('attacker_unit_ids', 0x18), ('defender_unit_ids', 0x20)):
                bp = loaded.q(sp + off)
                loaded.require(bp, 'CLandCombatant')
                ids = []
                for up in loaded.array(bp + 0x20, 4096):
                    loaded.require(up, 'CArmy')
                    if loaded.i(up + 0x18) != 51:
                        raise ObservationError('unexpected combat unit handle')
                    ids.append(loaded.i(up + 0x1c))
                sides[name] = ids
            if not own_ids_.intersection(sides['attacker_unit_ids'] + sides['defender_unit_ids']):
                continue
            province = loaded.q(sp + 0x28)
            loaded.require(province, 'CProvince')
            if loaded.i(sp + 8) != 62:
                raise ObservationError('unexpected land combat handle')
            combats.append({'combat_id': loaded.i(sp + 0xc), 'province_id': loaded.i(province + 0xa4), **sides})
        own_set = {u['unit_id'] for u in first['world']['own_units']}
        side_damage = {}
        for cp in loaded.array(gs + 0x268, 4096):
            if not is_land_combat(cp):
                continue
            sp = cp + 0x10
            cid = loaded.i(sp + 0xc)
            dmg = {}
            for name, off in (('attacker', 0x18), ('defender', 0x20)):
                bp = loaded.q(sp + off)
                loaded.require(bp, 'CLandCombatant')
                dmg[name] = struct.unpack('<q', p.read(bp + 0x180, 8))[0] / 100000
            side_damage[cid] = dmg
        for combat in combats:
            # Every combat in the official active manager list is ongoing; ended
            # combats leave the list, so 'ended' is never produced here.
            combat['phase'] = 'ongoing'
            dmg = side_damage.get(combat['combat_id'])
            if dmg:
                ours_attacking = bool(own_set.intersection(combat['attacker_unit_ids']))
                ours, theirs = ('attacker', 'defender') if ours_attacking else ('defender', 'attacker')
                combat['casualties'] = {'our_org_loss': round(dmg[ours], 5),
                                        'enemy_org_loss': round(dmg[theirs], 5)}
        for unit in first['world']['own_units']:
            for combat in combats:
                if unit['unit_id'] in combat['attacker_unit_ids'] + combat['defender_unit_ids']:
                    unit.update(in_combat=True, combat_id=combat['combat_id'])
                    break
        # Combat-revealed opponents (fog-honest: a player sees whom they fight).
        # Only CArmy objects named in our own active combats. relation 'enemy'
        # only when the native has-war getter 0x748400 path says at war.
        own_ids = {u['unit_id'] for u in first['world']['own_units']}
        _, country_ptrs = array(gs + 0x310, 2048)
        def at_war(idx):
            diplomacy = q(co + 0xF88)
            if not ptr(diplomacy) or not 0 <= idx < len(country_ptrs):
                return None
            rel = q(q(diplomacy + 8) + 8 * idx)
            if not ptr(rel):
                return False
            war = q(rel + 0x2E8)
            return bool(ptr(war) and p.read(war + 0x49, 1)[0] == 0)
        def tag_of(idx):
            data, cap_, n = struct.unpack('<QII', p.read(gs + 0x358, 16))
            if not 0 <= idx < n <= cap_:
                return None
            raw = p.read(data + idx * 32, 32)
            size = struct.unpack_from('<Q', raw, 16)[0]
            t = raw[:size].decode('ascii', 'replace') if size <= 15 else ''
            return t if len(t) == 3 and t.isalnum() else None
        visible = []; visible_evidence = []
        for combat in combats:
            for side in ('attacker_unit_ids', 'defender_unit_ids'):
                for uid in combat[side]:
                    if uid in own_ids or any(v['unit_id'] == uid for v in visible):
                        continue
                    ap = resolve_handle(Adapter(), 0x33, uid, p.base)
                    if not ptr(ap) or q(ap) - p.base != profile['vtable_rvas']['CArmy']:
                        visible_evidence.append({'unit_id': uid, 'omitted': 'not a primary CArmy'})
                        continue
                    owner_idx = i(ap + 0x1E0)
                    war = at_war(owner_idx)
                    rdata, rcap, rsize = struct.unpack('<QII', p.read(ap + 0x200, 16))
                    route = (list(struct.unpack('<' + 'I' * rsize, p.read(rdata, rsize * 4)))
                             if 0 < rsize <= rcap <= 64 and ptr(rdata) else [])
                    v = {'unit_id': uid, 'province_id': p.u32(ap + 0x28),
                         'owner': {'index': owner_idx},
                         'relation_to_player': 'enemy' if war else 'unknown',
                         'organization': struct.unpack('<q', p.read(ap + 0x428, 8))[0] / 100000,
                         'strength': {'current': struct.unpack('<q', p.read(ap + 0x420, 8))[0] / 100000},
                         'in_combat': True, 'combat_id': combat['combat_id'],
                         'order': {'type': 'unknown', 'target_province_ids': route[-1:],
                                   'path_province_ids': route},
                         'visibility': {'spotted': True}}
                    t = tag_of(owner_idx)
                    if t:
                        v['owner']['tag'] = t
                    visible.append(v)
                    visible_evidence.append({'unit_id': uid, 'owner_source': 'CArmy+0x1E0 logical_country',
                                             'war_source': 'native 0x748400 path', 'at_war': war})
        from input_loaded_fields import own_equipment_affected_units
        try:
            affected_equipment, affected_equipment_evidence = own_equipment_affected_units(loaded, co)
        except ObservationError as e:
            affected_equipment, affected_equipment_evidence = {}, {'omitted': str(e)}
        loaded_reads_checked=loaded.stable()
        if p.read(idler + 0x6c1, 1) != official_pause:
            raise ObservationError('official pause flag changed during capture')
        summary=read_campaign_summary(p,gs)['fields'];d=summary['date_full']
        y,m,day=map(int,d['ui'].split('-'))
        player={'index':res['player_index'],'tag':live_tag}
        # Tag comes from the live campaign table used by CountryTag::text.
        observation={'meta':{'game_time':{'year':y,'month':m,'day':day,'hour':d['ui_hour']},'player_country':player},
                     'world':{'own_units':first['world']['own_units'],'provinces':list(province_cache.values()),'leaders':leaders,'shortages':{'manpower':{'available':manpower_available}}}}
        observation['meta']['speed'] = 'pause' if official_pause == b'\1' else '1x'
        observation['world']['armies'] = armies
        observation['world']['army_groups'] = army_groups
        observation['world']['plans'] = plans
        observation['world']['combats'] = combats
        observation['world']['visible_units'] = visible
        # Wars involving the player: CWarRelation at relation+0x2E8 (t186/t225),
        # first +0x10, second +0x14, ongoing when byte +0x49 == 0. One row per war object.
        wars_seen = {}
        diplomacy_ = q(co + 0xF88)
        table_ = q(diplomacy_ + 8) if ptr(diplomacy_) else 0
        if ptr(table_):
            for idx in range(len(country_ptrs)):
                rel = q(table_ + 8 * idx)
                if not ptr(rel):
                    continue
                war = q(rel + 0x2E8)
                if ptr(war) and war not in wars_seen and p.read(war + 0x49, 1)[0] == 0:
                    a_idx, b_idx = i(war + 0x10), i(war + 0x14)
                    row = {'a': {'index': a_idx}, 'b': {'index': b_idx}, 'state': 'at_war'}
                    for side_, ix in (('a', a_idx), ('b', b_idx)):
                        tg = tag_of(ix)
                        if tg:
                            row[side_]['tag'] = tg
                    wars_seen[war] = row
        observation['world']['wars'] = list(wars_seen.values())
        # ---- Commander front view (extension, outside the input schema) ----
        # Controller of every province = owner country of its CControllerArea
        # (CProvince+0xD0) found in each country's +0x548 list (same proof as the
        # own-province controller field). Land adjacency as province_adjacencies.
        area_owner = {}
        for cidx, cptr in enumerate(country_ptrs):
            if not ptr(cptr):
                continue
            adata, acap, asize = struct.unpack('<QII', p.read(cptr + 0x548, 16))
            if 0 < asize <= acap <= 4096 and ptr(adata):
                for aptr in struct.unpack('<' + 'Q' * asize, p.read(adata, asize * 8)):
                    area_owner[aptr] = cidx
        n_prov = struct.unpack('<I', p.read(gs + 0x2BC, 4))[0]
        prov_arr = q(gs + 0x2B0)
        if not 0 < n_prov < 40000 or not ptr(prov_arr):
            raise ObservationError('province table implausible')
        prov_ptrs = struct.unpack('<' + 'Q' * n_prov, p.read(prov_arr, n_prov * 8))
        controller = {}
        for pid_, pp_ in enumerate(prov_ptrs):
            if pid_ and ptr(pp_):
                cidx = area_owner.get(q(pp_ + 0xD0))
                if cidx is not None:
                    controller[pid_] = cidx
        foes = {c for c in range(len(country_ptrs)) if at_war(c)}
        me = res['player_index']
        river_pairs = {}
        def land_neighbors(pp_):
            definition = q(pp_ + 0xB8)
            dd, dc, dn = struct.unpack('<QII', p.read(definition + 0x70, 16))
            if not (0 < dn <= dc <= 255) or not ptr(dd):
                return []
            rows = p.read(dd, dn * 0x30)
            out_ = []
            for k in range(dn):
                nid, typ = struct.unpack_from('<II', rows, k * 0x30 + 8)
                if typ in (0, 2, 3):
                    out_.append(nid)
                    if typ in (2, 3):
                        river_pairs.setdefault(pp_, set()).add(nid)
            return out_
        own_border, enemy_border = {}, {}
        own_nb = {}
        # Friendly ground: provinces of non-hostile countries where our divisions
        # stand (allies / subjects, e.g. Slovakia in 1939). Our divisions there
        # can attack neighbouring enemy provinces; the executor still only lets
        # move/redeploy end in our own provinces.
        friendly = {controller.get(u_.get('province_id')) for u_ in first['world']['own_units']} - foes - {me, None}
        friendly_prov = set()
        for pid_, cidx in controller.items():
            if cidx != me and cidx not in friendly:
                continue
            if cidx != me:
                friendly_prov.add(pid_)
            nb = land_neighbors(prov_ptrs[pid_])
            own_nb[pid_] = nb
            hostile = [n for n in nb if controller.get(n) in foes]
            if hostile:
                rv = river_pairs.get(prov_ptrs[pid_], set())
                own_border[pid_] = {'neighbors': nb, 'enemy_neighbors': hostile,
                                    'river_crossing_to': sorted(n for n in hostile if n in rv)}
                if cidx != me:
                    own_border[pid_]['friendly_controller'] = tag_of(cidx)
                for n in hostile:
                    enemy_border[n] = controller[n]
        # terrain / fort of the enemy provinces on our border (same readers as own provinces)
        enemy_terrain = {}
        for n in enemy_border:
            try:
                pp_ = prov_ptrs[n]
                tptr = q(q(pp_ + 0xB8) + 0xA8)
                row = {'terrain': string(tptr + 0x18) or None, 'victory_points': i(pp_ + 0x38)}
                try:
                    lvl, _fe = province_fort_level(loaded, pp_, building_templates['bunker'])
                    if lvl is not None:
                        row['fort_level'] = lvl
                except Exception:
                    pass
                enemy_terrain[n] = row
            except Exception:
                continue
        foe_counts = {tag_of(c) or str(c): sum(1 for v in controller.values() if v == c) for c in foes}
        # ---- map topology for the commander ----
        from collections import deque
        region_of = {}
        regions = []
        for start in sorted(own_nb):
            if start in region_of:
                continue
            rid = len(regions)
            members = []
            dq = deque([start]); region_of[start] = rid
            while dq:
                cur = dq.popleft(); members.append(cur)
                for n in own_nb.get(cur, []):
                    if n in own_nb and n not in region_of:
                        region_of[n] = rid; dq.append(n)
            regions.append(members)
        # hops from every own province to the nearest own border province, per region
        hops = {pid_: 0 for pid_ in own_border}
        dq = deque(own_border)
        while dq:
            cur = dq.popleft()
            for n in own_nb.get(cur, []):
                if n in own_nb and n not in hops:
                    hops[n] = hops[cur] + 1; dq.append(n)
        # enemy key provinces (victory points) and their distance from our territory
        enemy_nb_cache = {}
        def nb_any(pid_):
            if pid_ in own_nb:
                return own_nb[pid_]
            if pid_ not in enemy_nb_cache:
                enemy_nb_cache[pid_] = land_neighbors(prov_ptrs[pid_]) if ptr(prov_ptrs[pid_]) else []
            return enemy_nb_cache[pid_]
        foe_prov = {pid_ for pid_, cidx in controller.items() if cidx in foes}
        depth = {pid_: 1 for pid_ in enemy_border}
        dq = deque(enemy_border)
        while dq:
            cur = dq.popleft()
            for n in nb_any(cur):
                if n in foe_prov and n not in depth and controller.get(n) == controller.get(cur):
                    depth[n] = depth[cur] + 1; dq.append(n)
        key_targets = []
        for pid_ in foe_prov:
            vp = i(prov_ptrs[pid_] + 0x38)
            if 0 < vp <= 100000 and pid_ in depth:
                key_targets.append({'province_id': pid_, 'victory_points': vp,
                                    'owner': tag_of(controller[pid_]), 'hops_from_our_land': depth[pid_]})
        key_targets.sort(key=lambda r: (-r['victory_points'], r['hops_from_our_land']))
        # ---- encirclement indicators (for key-moment detection) ----
        # Enemy: connected components of each foe's land, built only from provinces
        # reachable from our border (bounded). A component cut off from the foe's
        # largest component is a pocket. Our side: small own regions = our pockets
        # (the stable exclaves such as East Prussia are reported too; the loop
        # compares against the previous tick).
        pockets = []
        for foe in foes:
            tag_ = tag_of(foe)
            if tag_ not in ('POL',) and len([1 for v in controller.values() if v == foe]) > 400:
                continue  # large overseas empires: skip (cost); front-line foe only
            members = [pid_ for pid_, c in controller.items() if c == foe]
            seen_ = {}
            comps = []
            for s in members:
                if s in seen_:
                    continue
                cid = len(comps); comp = []
                dq = deque([s]); seen_[s] = cid
                while dq:
                    cur = dq.popleft(); comp.append(cur)
                    for n in nb_any(cur):
                        if controller.get(n) == foe and n not in seen_:
                            seen_[n] = cid; dq.append(n)
                comps.append(comp)
            comps.sort(key=len, reverse=True)
            for comp in comps[1:]:
                ours_around = set()
                for x in comp:
                    for n in nb_any(x):
                        if controller.get(n) == me:
                            ours_around.add(n)
                if ours_around:  # cut off by us, not a natural island/colony
                    pockets.append({'owner': tag_, 'provinces': len(comp), 'sample': sorted(comp)[:8],
                                    'our_provinces_around': len(ours_around)})
        # near-closed: enemy border provinces whose land neighbours are mostly ours
        near_closed = []
        for pid_ in enemy_border:
            nb = nb_any(pid_)
            if len(nb) >= 3:
                ours = sum(1 for n in nb if controller.get(n) == me)
                if ours / len(nb) >= 0.75:
                    near_closed.append({'province_id': pid_, 'owner': tag_of(controller[pid_]),
                                        'ours': ours, 'neighbors': len(nb)})
        topology = {
            'regions': [{'region': rid, 'provinces': len(m),
                         'border_provinces': sorted(x for x in m if x in own_border)}
                        for rid, m in enumerate(regions)],
            'region_of_province': region_of,
            'hops_to_border': hops,
            'key_targets': key_targets[:40],
            'enemy_pockets': pockets,
            'near_closed': near_closed,
            'own_region_sizes': sorted((len(m) for m in regions), reverse=True),
            'source': 'BFS over land adjacency (types 0/2/3) of own-controlled provinces; '
                      'enemy depth BFS inside the same enemy controller; VP = CProvince+0x38',
        }
        # Provinces of ours facing countries we are NOT at war with but must not
        # leave bare (western neighbours); divisions there are kept in place.
        watch_tags = {'FRA', 'BEL', 'HOL', 'LUX', 'ENG'}
        watch_idx = {c for c in range(len(country_ptrs)) if tag_of(c) in watch_tags and c not in foes}
        own_watch = []
        own_watch_detail = {}
        if watch_idx:
            for pid_, cidx in controller.items():
                if cidx != me:
                    continue
                facing_tags = sorted({tag_of(controller.get(n)) for n in land_neighbors(prov_ptrs[pid_])
                                      if controller.get(n) in watch_idx})
                if facing_tags:
                    own_watch.append(pid_)
                    own_watch_detail[pid_] = facing_tags
        commander_ext = {
            'own_border': [{'province_id': k, **v} for k, v in sorted(own_border.items())],
            'enemy_border': [dict({'province_id': k, 'controller': {'index': v, 'tag': tag_of(v)}},
                                  **enemy_terrain.get(k, {}))
                             for k, v in sorted(enemy_border.items())],
            'enemy_controlled_provinces': foe_counts,
            'own_controlled_provinces': sum(1 for v in controller.values() if v == me),
            'own_watch_border': sorted(own_watch),
            'own_watch_facing': {str(k): v for k, v in sorted(own_watch_detail.items())},
            'topology': topology,
            'source': 'CProvince+0xD0 area -> country +0x548 lists; adjacency rows type 0/2/3',
        }
        mp_missing = sorted(e['unit_id'] for e in manpower_evidence if e['engine_missing_formula'] > 0)
        if mp_missing:
            observation['world']['shortages']['manpower']['affected_unit_ids'] = mp_missing
        equipment_rows = {x['equipment_type']: dict(x) for x in equipment_stockpile}
        for name, ids in affected_equipment.items():
            equipment_rows.setdefault(name, {'equipment_type': name})['affected_unit_ids'] = ids
        if equipment_rows:
            observation['world']['shortages']['equipment'] = list(equipment_rows.values())
        result = {'captured_at':datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-5),'EST')).isoformat(),
                'time_zone':'America/New_York (EST)','pid':p.pid,'exe_sha256':digest,
                'game_version':profile['game_version'],'read_only':True,'complete_input':False,
                'full_schema_validated':False,'observation':observation,
                'evidence':{'session':session['session'],'player_source':res['source'],
                            'speed_setting':speed+1,'pause_flag':official_pause[0],'pause_source':'CInGameIdler+0x6c1; before/after equal',
                            'core_scalar_double_read_equal':True,'clock_player_header_stable':True,
                            'terrain_source':'live loaded CTerrainType; no base map or history fallback',
                            'country_tag_source':'live GS+0x358 indexed MSVC table; CountryTag::text 0xc08223',
                            'victory_points_source':'live CProvince+0x38 named victory_points; optional rename+0x40',
                            'neighbors_source':'live [CProvince+0xb8]+0x70 stride 48 target +8; types 0/2/3 only; 14a6540/ab3660',
                            'has_river_crossing_source':'same adjacency records; type in {2,3} per 0x12971a0 range check; object neighbor_id->bool',
                            'loaded_dependent_reads_rechecked':loaded_reads_checked,
                            'army_collection':army_evidence,'army_group_collection':army_group_evidence,'plan_collection':plan_evidence,
                            'affected_equipment_collection':affected_equipment_evidence,
                            'supply_collection':supply_evidence,
                            'hp_current_max_collection':hp_evidence,'unit_manpower_collection':manpower_evidence,'country_manpower_collection':manpower_available_evidence,'equipment_stockpile_collection':equipment_stockpile_evidence,'reinforcement_request_collection':reinforcement_request_evidence,'official_country_need_collection':official_need_evidence,
                            'building_definition_collection':building_definition_evidence,'fort_collection':fort_evidence,'leader_collection':leader_evidence,'infrastructure_collection':infrastructure_evidence,'neighbor_collection':neighbor_evidence,
                            'combat_width_source':'live loaded CSubUnitDefinition+0x58; named combat_width parser; supports empty',
                            'template_handle_registry_checks':len(template_cache),'battalion_crosschecks':extra,
                            'visible_units_collection':{'scope':'opponents in our own active combats only','rows':visible_evidence},
                            'units_in_transit_province_pair_differs':transit_units,
                            'non_land_combats_skipped':skipped_non_land,
                            'tolerant_omissions':{'strength_max_units':omitted_max,'templates':template_notes},
                            'registered_self_provinces':{k:len(v) for k,v in area_memberships.items()},
                            'province_relation_scope':'only current country registrations; no contested ownership contrast accepted',
                            'combats_array':_pdx_array(p,gs+0x268),
                            'coverage':'country CO_ARMIES only; no independent full handle-table sweep',
                            'consistency_limit':'bounded non-atomic observation; template/terrain pointers not frozen'},
                'commander_ext':commander_ext,
                'blocking_checks':{'units':[{'unit_id':u['unit_id'],'errors':unit_blockers(u)} for u in first['world']['own_units']],
                                   'provinces':'building levels omitted for damaged/overlay states unaccepted; absent registered type returns native0',
                                   'meta':'policy/config allow_write/geography_scope not supplied by memory',
                                   'other':'policy/config, feedback ledger, visibility, incomplete plans/combats, shortages, wars not completed'}}
        from jsonschema import Draft202012Validator
        schema=json.loads((Path(__file__).resolve().parent/'tables/generalissimo_input.schema.json').read_text(encoding='utf-8'))
        schema_errors=list(Draft202012Validator(schema).iter_errors(observation))
        result['full_schema_validated']=True
        result['schema_validation']={'valid':not schema_errors,'error_count':len(schema_errors),
            'errors':[{'path':list(e.path),'message':e.message} for e in schema_errors]}
        # Schema shape alone cannot certify key nonempty-state semantic coverage.
        # complete_input remains False until that independent acceptance exists.
        return result
    finally:p.close()


def capture(retries: int = 3):
    from input_observation import ObservationError
    last=None
    for attempt in range(retries):
        try:
            result=_capture_once()
            result['evidence']['capture_attempts']=attempt+1
            result['evidence']['capture_variant']='live_input tolerant'
            return result
        except ObservationError as e:
            last=e
            if 'changed' not in str(e):
                raise
            time.sleep(0.5)
    raise last
