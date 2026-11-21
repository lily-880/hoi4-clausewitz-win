from pathlib import Path
import py_compile,json
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');p=R/'calling/input_capture_live.py';s=p.read_text(encoding='utf-8')
def rep(old,new):
 global s
 assert s.count(old)==1,old;s=s.replace(old,new)
rep("        if speed!=0:raise ObservationError('speed setting not 1x; not changed')","""        if speed!=0:raise ObservationError('speed setting not 1x; not changed')
        idler = int(session['signals']['idler_ptr'], 16)
        require_class(idler, 'CInGameIdler')
        official_pause = p.read(idler + 0x6c1, 1)
        if official_pause not in (b'\\0', b'\\1'):
            raise ObservationError('invalid official pause flag')""")
rep('        from input_loaded_fields import own_plans, own_active_combats','''        from input_loaded_fields import (own_plans, own_active_combats, own_armies,
            own_army_groups, unit_formation_army_id, unit_formation_army_group_id)
        armies, army_evidence = own_armies(loaded, co)
        army_groups, army_group_evidence = own_army_groups(loaded, co)
        for unit, up in zip(first['world']['own_units'], army_ptrs):
            army_id, _ = unit_formation_army_id(loaded, up)
            group_id, _ = unit_formation_army_group_id(loaded, up)
            formation = {}
            if army_id is not None:
                formation['army_id'] = army_id
            if group_id is not None:
                formation['army_group_id'] = group_id
            if formation:
                unit['formation'] = formation''')
rep('        loaded_reads_checked=loaded.stable()','''        loaded_reads_checked=loaded.stable()
        if p.read(idler + 0x6c1, 1) != official_pause:
            raise ObservationError('official pause flag changed during capture')''')
rep("        observation['world']['plans'] = plans","""        observation['meta']['speed'] = 'pause' if official_pause == b'\\1' else '1x'
        observation['world']['armies'] = armies
        observation['world']['army_groups'] = army_groups
        observation['world']['plans'] = plans""")
rep("'speed_setting':speed+1,'pause_flag':'unresolved; speed omitted from observation',","'speed_setting':speed+1,'pause_flag':official_pause[0],'pause_source':'CInGameIdler+0x6c1; before/after equal',")
rep("'loaded_dependent_reads_rechecked':loaded_reads_checked,","'loaded_dependent_reads_rechecked':loaded_reads_checked,\n                            'army_collection':army_evidence,'army_group_collection':army_group_evidence,'plan_collection':plan_evidence,")
rep("'meta':'speed missing; official pause bit unverified',","'meta':'policy/config allow_write/geography_scope not supplied by memory',")
rep("'other':'policy/config, feedback ledger, visibility, formations, plans, combats, shortages, wars not completed'","'other':'policy/config, feedback ledger, visibility, incomplete plans/combats, shortages, wars not completed'")
p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True)
(R/'research/t199_checkpoint.md').write_text('''# t199 checkpoint（严格只读）

本段禁止Post、WriteProcessMemory、remote Execute、改变pause/speed、读写存档及commit/push。用户授权本机活体只读采集与本地代码修复。没有导入或调用Post helper；未打开闸门。pid12948开段pause1、speed槽0、日期1936-01-02 15:00，4个已读计划均executing=false。

## 块1：完整capture原始端到端
calling/input_capture_live.py --out research/t199_full_capture.json 已成功完成，21师/12省/4模板/4计划/2战斗，5个师有in_combat=true。新增字段无schema类型/额外键错误；但完整schema有53个缺少必填字段错误，complete_input=false，不能称全合同通过。计划path非空[2072,7944]、战斗成员对应t198活体证据。没有把其余16师的未知状态填成false。
发现旧入口没有接上早已验证的meta.speed、army/army_group与师formation，且evidence仍写pause unresolved。已修复这些本地导出接线，添加官方pause位前后读取一致性检查，不改任何游戏状态；清单不因此增加字段。

## 块2：现存证据的离线语义排查
保存t199_named_strings/xrefs和_t199_clip_*纯静态反汇编。未调用这些地址。
- Combat writer0x147fe80的day/duration是整数（现有23/23），不能直接当started_at/ended_at。主vt+0x60只比较duration与全局阈值，不足以命名为HasEnded；主vt+0x48进一步检查双方阵营集合和单位非空，也不能擅命名phase。无结束样本，不由“表里有对象”直接升格ongoing。
- CCombatant+0xB8 token losses走0x2545f90定点序列化；当前双方均0，且没有证明这是schema要求的人力伤亡或组织损失。HP损耗不等于人力损耗。casualties不升格。
- CArmy+0x240 token movement_progress是qword定点，不是float；它不提供ETA小时，未证明是schema预期的归一化progress。保留原始证据，不将453600机械塞进eta。
- 官方命名断言仍只有ORDER_MOVE=1、ORDER_INVASION=3；现有全部type2，且Fallback命令也产生type2，故不能凭命令名统一输出frontline。axis/status未有独立语义链。
- CSupplyConsumer writer仅有disrupted_supply/motorization_level/countries；CSupplyConsumer身份及供应计算关系仍未接上己方CArmy。受损/参战本身不能证明缺补给或孤立，不能虚构ratio。

## 暂停故障：仅离线边界
保留t198_order_sample.json历史命令顺序与Post返回、t198_pause_recovery.json；没有复现、没有新预制暂停命令、没有调用游戏Execute。返回1不代表异步消费后状态已改变；具体原因未由历史数据唯一确定，不将创建顺序或队列延迟假设冒充根因。
''',encoding='utf-8')
print('PATCHED LOCAL CAPTURE; INVENTORY UNCHANGED')
