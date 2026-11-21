"""t223 frozen replay only. No live reads, generic integration or schema export.
Renderer opacity is not confidence; combat membership is not visibility.
"""
import hashlib
CODE_HASHES = {'t223_timed_activity_equipment_consumers.json': {'0xb88640': 'f410551372dd0d98dc9a1ea4fa6bf85565ad67011f44cded728e6f8c111345e0'}, 't223_timed_activity_receiver_leaves.json': {'0xd49ad0': '2d394acb187eb0e74590d60475c45bb52480a7d11803608e6f2fab2118e11a83'}, 't223_observer_visibility_getter.json': {'0x16b2eb0': '770863c60436d56d260a17edb6d6d9908bcdfe69ccd4c9f8fa9899cdb8fe9d64', '0xc539d0': '35a6441a7ae9d9b1bf5ac8c731f2ec8b7b95d0bf80f93a74aba727016dbe27df'}, 't223_live_province_overlay_controls.json': {'0x5a5210': '8ee76a6b8caebc02e6098356d455534e92b3652bbe729f259a3ef50f0737ab09'}, 't223_visibility_renderer_root_and_gate.json': {'0x131c770': '2061774cf7a01a2138739485fedf21d2b27ffdad69aa0c392e1dea6f00dfe6df'}, 't223_independent_counter_opacity_consumers.json': {'0x170bda0': '748dbaf413b8e845245924d386af396c15a9a1cdf61f4a5f63ca2f7e7ed4c805', '0x134ae00': '2306aab913f4a2c4645404d30ce907f91252b82846ee364666908e6f2deba618'}, 't223_fog_switch_semantic_binding.json': {'0x26ff10': 'af2bff3fcca3762981494cfedb4a66904edc7a2b0debe009c127b397ce87d4dc', '0x2b6270': '4950114eecb120fbb07236cc084e132c40df1799b4a5112da538e405cedb98a7'}, 't223_overlay_wrapper_leaf.json': {'0x17f7e0': 'da54ad8b6a68efce8e2cc81a99e98200efd33d805a34cf4e853404376bd929a8'}, 't223_current_overlay_selector_control.json': {'0xc55df0': '5fa5feb9d7b4c530da2939ae7326d0ea26ee3b4bff39e8c77b7817824095edfb'}}
CODE_HASHES['t223_observer_visibility_getter.json']['0xc085f0']='acab2dadf30b1cb58aae3a931aa3d605898b49f7ff49e0b6e46e2b15a27c7e74'
class Unproved(ValueError): pass

def integer(x):
    if type(x) is not int: raise Unproved('integer required')
    return x

def ordinary_land_opacity(tier,overlay):
    # Only arithmetic fragment, for offline edge tests. Not full visibility.
    if integer(tier) not in (0,1,2,3): raise Unproved('unproved observer tier')
    if not 0<=integer(overlay)<=255: raise Unproved('invalid overlay byte')
    return max((0,150,250,250)[tier],overlay)

def replay(docs):
    baseline=None
    for d in docs.values():
        if 'before' not in d:continue
        g=d['before']
        if d['after']!=g:raise Unproved('guard changed')
        if baseline is None:baseline=g
        if g!=baseline:raise Unproved('mixed session')
        if (g['pid']!=10288 or g['base']!='0x7ff758fc0000' or g['pause']!=1 or g['speed_slot']!=0 or
            g['hour_tick']!=60781105 or g['country_index']!=3 or any(g['markers'].values())):raise Unproved('session gate')
    for n,fs in CODE_HASHES.items():
        for a,h in fs.items():
            f=docs[n]['functions'][a]
            if f['unresolved_edges']:raise Unproved('unclosed required CFG')
            if f['sha256']!=h or hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()!=h:raise Unproved('native bytes')
    def atoms(n,a,ss):
        asm=docs[n]['functions'][a]['asm']
        if any(s not in asm for s in ss):raise Unproved('native semantic binding')
    atoms('t223_timed_activity_equipment_consumers.json','0xb88640',[
        'b8878b mov rcx, qword ptr [rax + 0xf70]','b88792 call 0xd49ad0',
        'b887ff cmp qword ptr [rax], 0xc350','b88818 cmp qword ptr [rax], 0xc350'])
    atoms('t223_timed_activity_receiver_leaves.json','0xd49ad0',['d49ad0 lea rax, [rcx + 0x78]'])
    activity=docs['t223_activity_receiver_identity.json']
    if activity['status_class']!='.?AVCDeploymentStatus@@' or activity['own_plan_arrays_read']!=0:
        raise Unproved('activity receiver is not proved battle plan')
    if activity['activity_request_count']!=0:raise Unproved('no positive activity replay scoped')
    atoms('t223_visibility_renderer_root_and_gate.json','0x131c770',[
        '131c82e call 0x16b2eb0','131c833 cmp al, 0x96','131c835 jae 0x131c9a4'])
    atoms('t223_independent_counter_opacity_consumers.json','0x170bda0',[
        '170bf85 call 0x16b2eb0','170bf8a cmp al, 0xfa','170bf8c jb 0x170c237'])
    atoms('t223_independent_counter_opacity_consumers.json','0x134ae00',[
        '134af20 call 0x16b2eb0','134af25 cmp al, 0x96','134af27 jb 0x134b020'])
    atoms('t223_observer_visibility_getter.json','0x16b2eb0',[
        '16b3083 mov ebx, 0x96','16b308a mov ebx, 0xfa','16b3102 cmova ebx, eax',
        '16b3111 mov r8d, 0x24b','16b315a cmp ebx, r15d','16b3179 mov al, 0xff'])
    atoms('t223_fog_switch_semantic_binding.json','0x26ff10',[
        '26ff63 lea rax, [rip + 0x253d276]','26ff6a lea rdx, [rip + 0x253d257]',
        '26ff71 test r9b, r9b','26ff74 cmove rdx, rax'])
    b=docs['t223_visibility_bypass_and_sharing_predicate.json']
    if b['bypass_switch_rva']!='0x33ddaaa' or b['bypass_switch_byte']!=1:raise Unproved('live fog gate')
    if not any(x['text']=='Fog of War is now ON.' and x['rva']=='0x27ad1c8' for x in b['literals']):raise Unproved('fog semantic label')
    mod=docs['t223_renderer_modifier_absence_control.json'];ids=mod['id_list']
    if mod['modifier_id']!='0x24b' or mod['matches'] or 0x24b in ids:raise Unproved('conditional modifier unsupported')
    if ids!=sorted(set(ids)) or len(ids)!=mod['entry_count']:raise Unproved('modifier bound/order')
    atoms('t223_live_province_overlay_controls.json','0x5a5210',[
        '5a526c cmp rsi, r10','5a526f je 0x5a5305','5a530d mov qword ptr [rbx], rdi'])
    tiers=docs['t223_own_combat_observer_tier_controls.json'];samples=docs['t223_live_province_overlay_controls.json']
    if tiers['observer_index']!=3 or samples['fog_enabled_byte']!=1 or not samples['overlay_present']:raise Unproved('observer overlay gate')
    if [c['combat_id'] for c in tiers['combats']]!=[3096,3097,3072]:raise Unproved('not scoped own combats')
    if tiers['rejected']!=[{'unit_id':4652,'handle_type':4713,'reason':'unsupported identity, no observer table read'}]:raise Unproved('identity rejection changed')
    remap=docs['t223_subject_country_remap_control.json']['remap_indices']
    if remap.get('3')!=3:raise Unproved('observer remap changed')
    by={}
    for row in tiers['rows']:
        key=(row['owner_tag'],row['unit_id'])
        if key in by or row['handle_type']!=51 or row['kind']!=0:raise Unproved('subject identity')
        # Scene has no observer rows. Empty is not equivalent to invisible:
        # ownership/sharing can return tier3, and overlay independently dominates.
        if row['entries'] or row['observer3_matches']:raise Unproved('nonempty observer table outside current proof')
        by[key]=row
    result=[];seen=set()
    for row in samples['rows']:
        key=(row['owner_tag'],row['unit_id'])
        if key in seen or key not in by or row['handle_type']!=51 or row['kind']!=0:raise Unproved('overlay subject identity')
        seen.add(key)
        if row['own']!=by[key]['own'] or row['geometry_low_bits']!=1 or not row['current_province_selected_by_native']:
            raise Unproved('not qualified ordinary land overlay')
        overlay=integer(row['raw_province_overlay_byte'])
        if row['own']:
            if row['owner_tag']!=3:raise Unproved('own country mismatch')
            value=255  # direct owner-tag equality shortcut in16B2EB0
        else:
            if str(row['owner_tag']) not in remap or remap[str(row['owner_tag'])]==remap['3']:
                raise Unproved('foreign direct tag-remap shortcut not covered')
            low=ordinary_land_opacity(0,overlay);high=ordinary_land_opacity(3,overlay)
            if low!=high:raise Unproved('unresolved sharing override affects opacity')
            value=low
        result.append({'unit_id':row['unit_id'],'owner_tag':row['owner_tag'],'own':row['own'],
                       'native_renderer_byte':value,'passes150':value>=150,'passes250':value>=250})
    if seen!=set(by):raise Unproved('subject coverage mismatch')
    return {'equipment_affected_plans_promoted':False,'visible_units_promoted':False,'spotted_promoted':False,
            'confidence_promoted':False,'own_plan_arrays_read':0,'subjects':result,
            'foreign_count':sum(not r['own'] for r in result),'foreign_byte250_count':sum(not r['own'] and r['native_renderer_byte']==250 for r in result),
            'scope':'native rendering evidence only; NOT a visible-unit feed, spotted export, or confidence probability'}
