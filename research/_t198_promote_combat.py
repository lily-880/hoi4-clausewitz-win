import json,struct,sys,hashlib
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'));sys.path.insert(0,str(R/'research'))
import _t197_setpath_zero_post as h
p=R/'calling/input_loaded_fields.py';src=p.read_text(encoding='utf-8');assert 'def own_active_combats(' not in src
src+='''\n\ndef own_active_combats(r, gs, country):
    """Official active manager list, restricted to combats involving own units (not a FoW unit feed)."""
    own_ids = set()
    for up in r.array(country + 0x290, 4096):
        r.require(up, 'CArmy')
        own_ids.add(r.i(up + 0x1c))
    result = []
    for cp in r.array(gs + 0x268, 4096):
        r.require(cp, 'CLandCombat')
        sp = cp + 0x10  # secondary serialization interface; writer 0x147fe80 offsets relative to it
        sides = {}
        for name, off in (('attacker_unit_ids', 0x18), ('defender_unit_ids', 0x20)):
            bp = r.q(sp + off)
            r.require(bp, 'CLandCombatant')
            ids = []
            for up in r.array(bp + 0x20, 4096):
                r.require(up, 'CArmy')
                if r.i(up + 0x18) != 51:
                    raise ObservationError('unexpected combat unit handle')
                ids.append(r.i(up + 0x1c))
            sides[name] = ids
        if not own_ids.intersection(sides['attacker_unit_ids'] + sides['defender_unit_ids']):
            continue
        province = r.q(sp + 0x28)
        r.require(province, 'CProvince')
        if r.i(sp + 8) != 62:
            raise ObservationError('unexpected land combat handle')
        result.append({'combat_id': r.i(sp + 0xc), 'province_id': r.i(province + 0xa4), **sides})
    return result


def own_unit_current_combat(r, gs, country, unit_id):
    """Positive official active-membership proof only; absence is not fabricated as false."""
    for combat in own_active_combats(r, gs, country):
        if unit_id in combat['attacker_unit_ids'] or unit_id in combat['defender_unit_ids']:
            return {'in_combat': True, 'combat_id': combat['combat_id']}
    return {}
'''
p.write_text(src,encoding='utf-8')
rows={
'world.own_units.in_combat':'以官方当前陆战成员表正例确认参战；本局师1831等确在己方陆战front中，未参战空值不冒写false。',
'world.own_units.combat_id':'从本人参与的官方当前陆战成员反查 CLandCombat 序号；师1831/1832对应战斗1。',
'world.combats.combat_id':'CLandCombat 序号在主对象+0x1C（序列化接口+0x0C）；本人参战活体编号1、2。',
'world.combats.province_id':'主对象+0x38指向CProvince，id在+0xA4；本人两场陆战位于13237、13238。',
'world.combats.attacker_unit_ids':'CLandCombat序列化接口+0x18指向攻击方；其+0x20官方unit数组含攻击师句柄，仅输出本人参与的战斗。',
'world.combats.defender_unit_ids':'CLandCombat序列化接口+0x20指向防守方；其+0x20官方unit数组含师1831/1832等，非猜测front与reserve的并集。'}
inv=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');lines=inv.read_text(encoding='utf-8').splitlines()
for name,note in rows.items():
 matches=[i for i,ln in enumerate(lines) if ln.startswith('| '+name+' |')];assert len(matches)==1;lines[matches[0]]=f'| {name} | 已验证 | {note} |'
text='\n'.join(lines)+'\n';Path(r'C:\Users\Lenovo\agent-tools\t198_inventory.md').write_bytes(text.encode('utf-8'))
p=R/'calling/tables/offsets_input_windows_1.19.5.json';d=json.loads(p.read_text(encoding='utf-8'));d['own_active_combat_t198']={'promoted':list(rows),'manager_array':'GS+0x268','serialization_interface':'CLandCombat primary+0x10','writer':'0x147fe80','handle':'primary+0x18 {62,id}','province_ptr':'primary+0x38','attacker_ptr':'primary+0x28','defender_ptr':'primary+0x30','side_combined_unit_array':'+0x20 / +0x2c','visibility_scope':'only actual own-involved current combats, not general visible_units','negative_in_combat':'omitted, not false'};p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (R/'research/t198_checkpoint.md').open('a',encoding='utf-8') as f:f.write('''\n## 块2：停止执行与暂停异常\n已官方 execute_order=0，计划1回读false；其余已读计划也均false。解除暂停后8秒采样期间date/progress未变，预先构造的恢复暂停命令Post返回1但回读仍pause=0（脚本断言失败，非超时）。此后核查发现时间在继续推进；另构造当前状态下的官方CPauseGame pause=1并Post成功，已回读pause=1，最终日期1936-01-02 15:00，比开段推进26小时。期间速度档始终0（1x），没有发进攻，但超出了预期短时窗口；不能写成“立即暂停成功”。原因未确定，今后不再1x，先查预制pause命令/异步消费时序。1829仍5010→8036，commandlist/full_path仍空，movement_progress raw从16800到453600。\n\n## 块3：自然出现的本人陆战\n恢复暂停后，官方GS+0x268现在有两场CLandCombat；secondary serialization interface在主对象+0x10。官方writer 0x147fe80字段必须加这0x10，不能拿主vt错误slot当serializer。两场id1/2，省13237/13238；己方防守成员分别1831/1832与1833/1834/1841，与本国CArmy指针精确对应。攻击方读取的是本人实际参战对手，不输出其他世界战况，更不把它当visible_units。\n升格6项：own_units.in_combat（只输出正例）、own_units.combat_id、combats.combat_id/province_id/attacker_unit_ids/defender_unit_ids。补上own_active_combats与own_unit_current_combat；无本人参与的战斗跳过。\n''')
import py_compile;py_compile.compile(str(R/'calling/input_loaded_fields.py'),doraise=True)
print('STAGED SHA',hashlib.sha256(text.encode()).hexdigest())
