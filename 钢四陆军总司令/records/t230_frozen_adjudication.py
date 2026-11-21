# Offline frozen adjudicator. No IO, no game backend, no production writes.
OWN_FRONT_IDS = (1278, 76, 70, 1734, 1735)
PLAYER_THEATRE = '0x23e02f93b20'
KIND = 66
COUNTRY_THEATRE_ARRAY_COUNT = 1
DESIRED_NAME = '_TotalFrontDesiredNrDivisions'
REQ_DIVS = 'REQ_DIVS'
GARRISON_HEADLINE = 'garrison_order_headline'
GARRISON_CONF = 'GARRISON_ORDER_CONF'
INVENTORY_SHA = '8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
PROD = {
 'calling/input_capture_live.py': 'e10bf427df1059c3f16873960bcbdabef826ef1dc058ad5e087b5a67d8087d37',
 'calling/input_loaded_fields.py': '1aecf151e7f221fa2f1a6b86b37a9d15bf2a44d0f7f649f552b2af8f808e65b5',
 'calling/tables/generalissimo_input.schema.json': '9a941dd3931b635591582b0d2ba3fe7ab1ceb3554a2d30af54154e61071b45ee',
 'calling/input_observation.py': '27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6',
}
NATIVE_CONTROLS = {
 '0x147c330': 'd47cee77d6354b55c8409394903552842feb1b9034e84a6b99cc88ee9bb735e6',
 '0xcec2e0': 'f421f2fca4a1bbcc7156a96fc752dfa7b8298bc006ca3c5488470faffd0369d3',
}
ACCEPTED = {
 '0x697db0': {'window_size':2326,'sha256':'f4a5bc064d01aead638d5c24dd686a360f782a8342e7590756645b8b9903949e','partial':False,'unresolved':[]},
 '0x177d240': {'window_size':5626,'sha256':'4e899f67a4ccd8add25917d6986fa48b85505b27d9f522f599027d5a775dd0d3','partial':True,'unresolved':[{'address':'0x177d3fa','reason':'indirect jump','operand':'rcx'}]},
 '0xf7be60': {'window_size':2173,'sha256':'1206a93105a587a509e03ff64da35e671253fbfa04aaef6aec406d7990d8a5c1','partial':False,'unresolved':[]},
 '0xf775e0': {'window_size':232,'sha256':'d93591b3654354b83433144556459bc397017de2fa45342b6a1341422d900f5c','partial':False,'unresolved':[]},
}

class Rejected(Exception):
    pass

def _need(cond,msg):
    if not cond: raise Rejected(msg)

def replay(literals, desired, membership, correction, inventory_bytes, inventory_sha, production, session, native_windows):
    # inventory
    _need(inventory_sha==INVENTORY_SHA,'inventory sha')
    _need('| 已验证 |'.encode() in inventory_bytes and inventory_bytes.count('| 已验证 |'.encode())==87,'verified count')
    _need(inventory_bytes.count('| 未验证 |'.encode())==29,'unverified count')
    _need(inventory_bytes.count('| 字段名 | 已验证/未验证 | 说明 |'.encode())==14,'tables')
    # session
    _need(session['pid']==10288 and session['base']=='0x7ff758fc0000' and session['country_index']==3,'session identity')
    _need(session['pause']==1 and session['speed_slot']==0 and session['hour_tick']==60781105,'session clock')
    _need(not any(session['markers'].values()),'open gates')
    # production
    _need(production==PROD,'production hashes')
    # windows
    for va,pin in ACCEPTED.items():
        w=native_windows[va]
        _need(w['window_size']==pin['window_size'] and w['sha256']==pin['sha256'],'window hash '+va)
        unresolved=w.get('unresolved_edges') or []
        if pin['partial']:
            _need(unresolved==pin['unresolved'],'expected partial unresolved '+va)
        else:
            _need(unresolved==[] and not (w.get('external_tails') or []),'unexpected tails '+va)
    # desired is named and must not export as missing
    texts=[row['text'] for row in literals]
    _need(any(DESIRED_NAME in (row.get('text') or '') for row in desired['literals']),'desired literal present')
    _need(desired['function']=='0x697db0','desired function')
    # REQ_DIVS garrison context
    req_texts=set(req['text'] for req in membership['req_divs_literals'])
    _need(REQ_DIVS in req_texts and GARRISON_HEADLINE in req_texts and GARRISON_CONF in req_texts,'req_divs garrison context')
    _need('BATTLE_PLANS_X_WILL_BE_ASSIGNED' in req_texts,'assignment literal is not missing')
    # own fronts
    fronts=correction['own_fronts']
    _need(correction['player_theatre']==PLAYER_THEATRE,'player theatre')
    _need(correction['country_theatre_array_count']==COUNTRY_THEATRE_ARRAY_COUNT,'single official theatre')
    _need(tuple(f['id'] for f in fronts)==OWN_FRONT_IDS,'own front ids')
    _need(all(f['kind']==KIND and f['theatre_back']==PLAYER_THEATRE and f['back_is_this_theatre'] for f in fronts),'own back-pointer')
    _need(correction['neighbor_front_counts']==[3,73,3,8],'neighbor counts recorded, not owned')
    _need(correction['overlap_offsets_are_neighbor_theatre_plus_50'] is True,'stride correction')
    # export rules
    exported=membership.get('exported_fields') or {}
    _need('world.shortages.missing_divisions' not in exported,'no missing_divisions export')
    _need(not membership.get('treat_desired_as_missing'),'desired is not missing')
    _need(not membership.get('treat_req_divs_as_missing'),'garrison REQ_DIVS is not missing')
    _need(not membership.get('treat_neighbor_fronts_as_own'),'neighbors are not own')
    _need(not membership.get('derived_required_minus_assigned_as_official_missing'),'no derived official missing')
    _need(not membership.get('infer_combat_result_from_selector_xor'),'no combat result inference')
    return {
        'promoted_fields':[],
        'own_front_ids':list(OWN_FRONT_IDS),
        'own_front_count':len(OWN_FRONT_IDS),
        'desired_named':DESIRED_NAME,
        'req_divs_scope':'garrison_order_ui_partial',
        'missing_divisions_promoted':False,
    }
