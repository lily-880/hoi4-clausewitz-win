from pathlib import Path
import json,hashlib,py_compile
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win')
p=R/'calling/input_loaded_fields.py';s=p.read_text(encoding='utf-8');assert 'def own_equipment_affected_units('not in s
s+='''\n\ndef own_equipment_affected_units(r, country):
    """Physical fielded shortage membership, not national demand or request-queue coverage.

    t199 proves matching canonical infantry_equipment buckets for all 21 own
    divisions, including full-strength 1843 and requestless under-equipped units.
    Unknown/absent buckets are NOT fabricated as zero; omit that whole type.
    """
    affected = {}
    incomplete = set()
    evidence = []
    for up in r.array(country + 0x290, 4096):
        r.require(up, 'CArmy')
        uid = r.i(up + 0x1c)
        template = r.q(up + 0x3b8)
        r.require(template, 'CReferencedDivisionTemplate')
        need = _typed_equipment_amounts(r, template + 0x120, 'CEquipmentArcheTypePool', 16, 8)
        current = _typed_equipment_amounts(r, up + 0x348, 'CEquipmentVariantPool', 24, 16)
        cur = {x['equipment_type']: x['amount_raw'] for x in current}
        for row in need:
            name = row['equipment_type']
            if name != 'infantry_equipment':
                continue  # no semantic acceptance for other equipment families yet
            affected.setdefault(name, [])
            if name not in cur:
                incomplete.add(name)
                continue
            short = row['amount_raw'] > cur[name]
            evidence.append({'unit_id': uid, 'equipment_type': name,
                'template_need_raw': row['amount_raw'], 'current_raw': cur[name], 'short': short})
            if short:
                affected[name].append(uid)
    return {k: sorted(set(v)) for k, v in affected.items() if k not in incomplete}, {
        'scope': 'physical template need versus fielded amount; not national demanded/deficit',
        'incomplete_types_omitted': sorted(incomplete), 'unit_comparisons': evidence}
'''
p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True)
p=R/'calling/input_capture_live.py';s=p.read_text(encoding='utf-8');old='        loaded_reads_checked=loaded.stable()';assert s.count(old)==1;s=s.replace(old,'''        from input_loaded_fields import own_equipment_affected_units
        affected_equipment, affected_equipment_evidence = own_equipment_affected_units(loaded, co)
        loaded_reads_checked=loaded.stable()''')
old="        if equipment_stockpile:observation['world']['shortages']['equipment']=equipment_stockpile";assert s.count(old)==1;s=s.replace(old,'''        equipment_rows = {x['equipment_type']: dict(x) for x in equipment_stockpile}
        for name, ids in affected_equipment.items():
            equipment_rows.setdefault(name, {'equipment_type': name})['affected_unit_ids'] = ids
        if equipment_rows:
            observation['world']['shortages']['equipment'] = list(equipment_rows.values())''')
old="'army_collection':army_evidence,'army_group_collection':army_group_evidence,'plan_collection':plan_evidence,";assert s.count(old)==1;s=s.replace(old,old+"\n                            'affected_equipment_collection':affected_equipment_evidence,");p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True)
name='world.shortages.equipment.affected_unit_ids';inv=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');lines=inv.read_text(encoding='utf-8').splitlines();ix=[j for j,x in enumerate(lines)if x.startswith('| '+name+' |')];assert len(ix)==1;lines[ix[0]]='| '+name+' | 已验证 | 本类型编制需求大于师实装的己方师编号；21师独立比对已证实infantry_equipment不足20师、1843足额，不以补充请求表代替完整师表。 |';raw=('\n'.join(lines)+'\n').encode('utf-8');Path(r'C:\Users\Lenovo\agent-tools\t199_inventory.md').write_bytes(raw)
p=R/'calling/tables/offsets_input_windows_1.19.5.json';d=json.loads(p.read_text(encoding='utf-8'));d['equipment_affected_units_t199']={'promoted':[name],'accepted_type':'infantry_equipment','criterion':'matching canonical type: template need raw > fielded current raw','template_need':'CArmy+0x3B8 -> CReferencedDivisionTemplate+0x120 CEquipmentArcheTypePool','current':'CArmy+0x348 CEquipmentVariantPool','coverage':'all 21 own units, not requests only','live_positive_count':20,'negative_unit':1843,'absent_bucket':'omit type; never infer zero','not_promoted':['demanded','deficit','affected_plan_ids']};p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (R/'research/t199_checkpoint.md').open('a',encoding='utf-8')as f:f.write('''\n## 块3：独立装备不足名单（新证明）\n完整capture揭示补充请求只有15师，不能当全部不足师。进一步严格只读遍历全部21师，使用此前官方证明的template+0x120编制类型需求与CArmy+0x348实装类型池作独立比较；两侧均为相同canonical infantry_equipment，有20师需求大于实装，1843恰480/480不入名单。特别是参战1831/1832/1833/1834/1841没有补充请求但确实不足；1829请求need=2而物理缺额=4，进一步证明请求表不能替代实装。\n升格world.shortages.equipment.affected_unit_ids，严格限定已证实的infantry_equipment类型，未知装备类型跳过，缺当前桶不补零而整类省略。仅表达“当前编制未足额”的成员，不宣称对计划的因果影响，不将物理缺额和1940请求需求冒称国家demanded/deficit，不将装备不足或HP损耗称人力伤亡。\n新reader已接入capture；清单待复制后读回SHA：'''+hashlib.sha256(raw).hexdigest()+'''。本段新升格1项；应为72已验证/44未验证。\n''')
print('STAGED_SHA256',hashlib.sha256(raw).hexdigest())
