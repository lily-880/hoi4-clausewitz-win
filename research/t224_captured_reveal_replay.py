"""t224 frozen narrow reveal-gate proof; no process access or production integration.
Not a complete visible feed. No relation/confidence export. The qualified adapter
is narrower than the native150 threshold: intermediate bytes remain out of scope.
"""
import hashlib,struct
CODE_HASHES = {'0x16b2eb0': '770863c60436d56d260a17edb6d6d9908bcdfe69ccd4c9f8fa9899cdb8fe9d64', '0xc539d0': '35a6441a7ae9d9b1bf5ac8c731f2ec8b7b95d0bf80f93a74aba727016dbe27df', '0xc085f0': 'acab2dadf30b1cb58aae3a931aa3d605898b49f7ff49e0b6e46e2b15a27c7e74', '0x748500': '73204a43b5e22a9a852a63a35df568d9a65a9e959cfa9c3c587d034146d516b1', '0x748490': '0d8ff672e9bfbb58ea63290feac2a76519300ea372851080857693d7be0d563c', '0x134ae00': '2306aab913f4a2c4645404d30ce907f91252b82846ee364666908e6f2deba618', '0x170bda0': '748dbaf413b8e845245924d386af396c15a9a1cdf61f4a5f63ca2f7e7ed4c805', '0x131c770': '2061774cf7a01a2138739485fedf21d2b27ffdad69aa0c392e1dea6f00dfe6df', '0x5a5210': '8ee76a6b8caebc02e6098356d455534e92b3652bbe729f259a3ef50f0737ab09', '0xc55df0': '5fa5feb9d7b4c530da2939ae7326d0ea26ee3b4bff39e8c77b7817824095edfb', '0x26ff10': 'af2bff3fcca3762981494cfedb4a66904edc7a2b0debe009c127b397ce87d4dc', '0x2b6270': '4950114eecb120fbb07236cc084e132c40df1799b4a5112da538e405cedb98a7', '0x17f7e0': 'da54ad8b6a68efce8e2cc81a99e98200efd33d805a34cf4e853404376bd929a8'}
class Unproved(ValueError): pass

def native_revealed(value):
    if type(value) is not int or not 0<=value<=255:raise Unproved('native byte required')
    return value>=150

def qualified_revealed(value):
    if value not in (0,250,255) or type(value) is not int:
        raise Unproved('unobserved byte branch outside qualified scope, NOT a different spotted threshold')
    return native_revealed(value)

def replay(docs):
    baseline=None
    for d in docs.values():
        if 'before' not in d:continue
        g=d['before']
        if d['after']!=g:raise Unproved('unstable guard')
        if baseline is None:baseline=g
        if baseline!=g:raise Unproved('mixed session')
        if g['pid']!=10288 or g['base']!='0x7ff758fc0000' or g['pause']!=1 or g['speed_slot']!=0 or g['hour_tick']!=60781105 or any(g['markers'].values()):
            raise Unproved('session gate')
    chain=docs['t224_native_reveal_chain.json']['functions']
    for a,h in CODE_HASHES.items():
        f=chain[a]
        if f['unresolved_edges']:raise Unproved('unclosed native chain')
        if f['sha256']!=h or hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()!=h:raise Unproved('native code mismatch')
    def atoms(a,ss):
        if any(s not in chain[a]['asm'] for s in ss):raise Unproved('semantic dataflow missing')
    atoms('0x134ae00',['134af20 call 0x16b2eb0','134af25 cmp al, 0x96','134af27 jb 0x134b020','134af80 lea rdx, [rip + 0x16d8cd1]'])
    atoms('0x131c770',['131c82e call 0x16b2eb0','131c833 cmp al, 0x96','131c835 jae 0x131c9a4'])
    atoms('0x748500',['748528 mov rax, qword ptr [rbx + 0x2e8]','748534 cmp byte ptr [rax + 0x49], 0','748538 jne 0x74854c','74853a xor al, al'])
    atoms('0xc539d0',['c539f8 call 0x748490','c53a1c jle 0xc53a44','c53a44 xor eax, eax'])
    atoms('0x16b2eb0',['16b3083 mov ebx, 0x96','16b308a mov ebx, 0xfa','16b3102 cmova ebx, eax','16b3111 mov r8d, 0x24b'])
    literals=docs['t224_consumer_semantic_literals.json']['consumer_literals']
    if not any(x['consumer']=='0x134ae00' and x['site']=='0x134af80' and x['literal']=='INTEL_DIVISION_REVEALED' for x in literals):
        raise Unproved('revealed name not independently bound')
    if not any(x['consumer']=='0x170bda0' and x['literal']=='deployed_general_base_plate' for x in literals):
        raise Unproved('250 consumer is not generic spotted')
    d=docs['t224_native_positive_negative_controls.json'];raw=docs['t224_reveal_operand_verification.json']
    if d.get('complete_visible_feed') or d['inspected_candidates']>64 or d['inspected_candidates']!=2:
        raise Unproved('bounded contrast not full feed')
    if d['inspection_limit']>64 or not 0<d['inspected_candidates']<=d['inspection_limit']<=d['unit_registry_count']:
        raise Unproved('candidate scope')
    if d['war_class']!='.?AVCWarRelation@@' or d['relation_class']!='.?AVCRelationStatus@@' or d['diplomacy_class']!='.?AVCDiplomacyStatus@@':
        raise Unproved('sharing branch receiver')
    if d['war_flag49']!=0 or raw['war_flag49_hex']!='00' or not d['sharing_false_immediate_branch']:
        raise Unproved('cannot prove sharing false without following other branches')
    rm=raw['remap_indices']
    if rm!={'3':3,'443':368} or d['owner_country_index']!=368 or d['observer_country_index']!=3:
        raise Unproved('tag equality/remap shortcut')
    ids=raw['modifier_id_list']
    if ids!=sorted(set(ids)) or len(ids)!=raw['modifier_entry_count'] or 587 in ids or not raw['modifier24b_absent']:
        raise Unproved('modifier absence not raw-proved')
    if not d['fog_enabled'] or raw['fog_enabled_byte']!=1:raise Unproved('fog enabled scope')
    by={}
    for row in raw['rows']:
        if row['unit_id'] in by:raise Unproved('duplicate selected subject')
        by[row['unit_id']]=row
    result=[];audit={}
    for label in ('positive','negative'):
        row=d[label]
        if not row:raise Unproved('live positive and negative both required')
        uid=row['unit_id'];b=by.get(uid)
        if b is None:raise Unproved('raw control join')
        if row['handle_type']!=51 or b['handle_type']!=51 or row['kind']!=0 or b['kind']!=0:
            raise Unproved('production51/kind unchanged')
        if row['owner_tag']!=443 or b['owner_tag']!=443 or row['province_id']!=b['province_id']:
            raise Unproved('fresh subject/province identity')
        if row['geometry_low_bits']!=1 or b['geometry_byte']&3!=1:raise Unproved('ordinary land selector only')
        overlay=b['province_overlay_byte']
        if type(overlay) is not int or overlay!=row['province_overlay'] or not 0<=overlay<=255:raise Unproved('overlay mismatch')
        if label=='positive':
            if overlay<250 or row['observer_table_read'] is not False:raise Unproved('positive overlay-dominance proof')
            value=overlay
        else:
            header=bytes.fromhex(b['observer_table_header_hex'])
            if len(header)!=16:raise Unproved('observer header')
            ptr,cap,n=struct.unpack('<QII',header)
            if not 0<=n<=cap<=4096 or n!=0 or row['observer_entry_count']!=0 or row['observer_matches'] or row['tier_from_table_or_default']!=0:
                raise Unproved('default zero tier requires actual empty header and sharing false')
            value=max(0,overlay)
        if value!=row['native_byte']:raise Unproved('native opacity recomputation')
        spotted=qualified_revealed(value)
        if spotted != (label=='positive'):raise Unproved('positive/negative contrast lost')
        audit[str(uid)]={'native_byte':value,'spotted':spotted}
        if spotted:result.append({'unit_id':uid,'visibility':{'spotted':True}})
    return {'visible_units':result,'control_audit':audit,'complete_visible_feed':False,
            'complete_input':False,'relation_exported':False,'confidence_exported':False,
            'scope':'known own-combat opponent443; type51 kind0 ordinary land; fogON; remap unequal; modifier24B absent; proven sharing-false branch; native bytes0/250/255 only'}
