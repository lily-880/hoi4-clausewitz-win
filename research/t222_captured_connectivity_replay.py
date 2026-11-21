"""Frozen t222 evidence replay only. No live APIs; no field export/promotion.
CProvince+D0 was initially labelled landmass provisionally in raw fixtures;
actual new RTTI is CControllerArea. Only that actual type is accepted here.
"""
import hashlib
CODE_HASHES = {'t222_isolation_entrances.json': {'0xe64c50': '92d09c38d41d525caffe43902c21fd305e5fa0f2509da7cf435f2212b9a524d4', '0xe653f0': '75fbd828015d690a0b2fa8eb43320fb9f102a924d8daaba72b656f5e94197a79'}, 't222_named_encirclement_predicates.json': {'0xc47c40': 'ba4ee2272097031cb87141eba0422ee2a7b50ae24247dfd571d0da3685afcf27', '0xc47880': '2eb25a387fd7d71ff5807c508bf9fb752bac7114214445233efb54fdfcaae335'}, 't222_hq_encirclement_branches.json': {'0x195e950': '2c76360920dc5cb0ebb44096ea7a9d8b1dfe4b5050605ef23b4b6662d9fc3bdd', '0x173eba0': 'e020e6887d23a307491c1bea1ce95aea72027b265630712a40a8d0ca8fc99409'}, 't222_capital_and_sea_leaf_closed.json': {'0x737f50': '9ac404d9d06f4f9ccbe1efca1116f9ac32e32e12294c7cdaa2ef62fdf2d344e9'}, 't222_province_registry_membership_closed.json': {'0xeef530': '9f03d26508477c62fbb4b74df5d0bfcc96354369a1af71505f8e1092f3367ad6'}, 't222_connectivity_leaves.json': {'0x12b6690': 'e91be375609d7e966b6f20227ee6011800f6d99106b55718f0448c297f12b68c'}}

class Unproved(ValueError): pass

def exact_int(x):
    if type(x) is not int: raise Unproved('integer required')
    return x

def native_connected_short_branch(row, home):
    if exact_int(row['handle_type']) != 51 or exact_int(row['unit_id']) <= 0:
        raise Unproved('unsupported identity; production51 unchanged')
    if exact_int(row['kind']) != 0: raise Unproved('nonarmy kind not covered')
    flag=exact_int(row['flag_1e'])
    if flag not in (0,1) or type(row['special']) is not bool: raise Unproved('invalid flag')
    if row['special']: return True,'special'
    if flag: return True,'consumer_flag'
    if row['landmass'] == home and home != '0x0': return True,'home_controller_area'
    # Do NOT infer disconnected: source-registry/area-hub hash fallback remains.
    raise Unproved('different controller-area fallback not independently replayed')

def replay(docs):
    baseline=None
    for d in docs.values():
        if 'before' not in d: continue
        g=d['before']
        if g != d['after']: raise Unproved('unstable guard')
        if baseline is None: baseline=g
        if g != baseline: raise Unproved('mixed-session evidence')
        if (g['pid']!=10288 or g['base']!='0x7ff758fc0000' or
            g['pause']!=1 or g['speed_slot']!=0 or g['hour_tick']!=60781105 or
            g['country_index']!=3 or any(g['markers'].values())): raise Unproved('session gate')
    for n,fs in CODE_HASHES.items():
        for a,h in fs.items():
            f=docs[n]['functions'][a]
            if f['sha256']!=h or hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()!=h:
                raise Unproved('native code mismatch')
            if f['unresolved_edges']: raise Unproved('unclosed required CFG')
    native=docs['t222_isolation_entrances.json']['functions']['0xe64c50']['asm']
    for atom in ['e64c61 cmp byte ptr [rcx + 0x2e], 0','e64caf cmp rdi, rax',
                 'e64cd7 call 0x7362c0','e64d06 call 0xeef530','e64d18 call 0x12b6690',
                 'e64d1f jns 0xe64d45']:
        if atom not in native: raise Unproved('connectivity dataflow missing')
    preds=docs['t222_named_encirclement_predicates.json']['functions']
    for a,atoms in {
        '0xc47c40':['c47c74 call 0xe64c50','c47c7b jne 0xc47c84','c47c7d mov al, 1'],
        '0xc47880':['c478bb call 0xe64c50','c478c2 jne 0xc478da','c478cd mov al, 1'],
    }.items():
        if any(atom not in preds[a]['asm'] for atom in atoms): raise Unproved('warning predicate polarity')
    hq=docs['t222_hq_encirclement_branches.json']['functions']
    if '173f5ca call 0xc47c40' not in hq['0x173eba0']['asm'] or '195f1f3 call 0xc47c40' not in hq['0x195e950']['asm']:
        raise Unproved('independent warning caller missing')
    refs=docs['t222_encircled_token_xrefs.json']['refs']
    if not any(x['site']=='0x173f5e6' and x['literal']=='HQ_WITHDRAWAL_BLOCKED_ENCIRCLED' for x in refs):
        raise Unproved('official name binding missing')
    identity=docs['t222_area_identity_control.json']
    if identity['rows'][0]['area_class']!='.?AVCControllerArea@@': raise Unproved('area is not a proved landmass')
    d=docs['t222_home_landmass_fallback_positive_controls.json']
    if d['country_tag']!=3 or d['capital_state_id']<=0 or d['capital_state_class']!='.?AVCState@@':
        raise Unproved('capital identity')
    candidates=[p for p in d['capital_provinces'] if p['country_tag']==3 and p['landmass']!='0x0' and exact_int(p['weight'])>0]
    if not candidates: raise Unproved('no capital controller-area')
    home=max(candidates,key=lambda p:p['weight'])['landmass']
    if home!=d['home_landmass']: raise Unproved('wrong capital controller-area')
    results={};rejected=[];flagzero=[];shortcut=[]
    for row in d['rows']:
        uid=exact_int(row['unit_id'])
        if uid in results or uid in rejected: raise Unproved('duplicate unit')
        if row['handle_type']!=51:
            if row['accepted_identity']: raise Unproved('unsupported acceptance')
            rejected.append(uid);continue
        if not row['accepted_identity'] or row['selected_country_tag']!=3: raise Unproved('own identity')
        connected,branch=native_connected_short_branch(row,home)
        rawbranch='home_landmass' if branch=='home_controller_area' else branch
        if row['native_connected'] is not connected or row['native_branch']!=rawbranch: raise Unproved('stale native branch')
        results[uid]={'native_connected':connected,'branch':branch}
        (flagzero if row['flag_1e']==0 else shortcut).append(uid)
    if d['isolation_positive_samples']!=0: raise Unproved('manufactured positive')
    return {'supported_units':len(results),'rejected_units':len(rejected),
            'flag_zero_but_connected':flagzero,'flag_shortcut_count':len(shortcut),
            'native_disconnected_count':0,'isolated_promoted':False,
            'component_type':'CControllerArea','results':results}
