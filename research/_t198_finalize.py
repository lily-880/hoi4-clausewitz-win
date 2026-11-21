import sys,json,hashlib,py_compile
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win')
# Wire the new bounded readers into actual partial captures before the dependent-read recheck.
p=R/'calling/input_capture_live.py';s=p.read_text(encoding='utf-8')
a='        loaded_reads_checked=loaded.stable()'
b='''        from input_loaded_fields import own_plans, own_active_combats
        plans, plan_evidence = own_plans(loaded, co)
        combats = own_active_combats(loaded, gs, co)
        for unit in first['world']['own_units']:
            for combat in combats:
                if unit['unit_id'] in combat['attacker_unit_ids'] + combat['defender_unit_ids']:
                    unit.update(in_combat=True, combat_id=combat['combat_id'])
                    break
        loaded_reads_checked=loaded.stable()'''
assert s.count(a)==1;s=s.replace(a,b)
a="        if equipment_stockpile:observation['world']['shortages']['equipment']=equipment_stockpile"
b="        observation['world']['plans'] = plans\n        observation['world']['combats'] = combats\n"+a
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s,encoding='utf-8');py_compile.compile(str(p),doraise=True)
# Freeze captured proof, not initial t197 SHA, as t198 acceptance baseline.
v=json.loads((R/'research/t198_validation.json').read_text(encoding='utf-8'))
with (R/'research/t198_checkpoint.md').open('a',encoding='utf-8') as f:
 f.write('''\n## 安全停止与最终状态\n恢复暂停后只读检查确认前线当前HP低于上限：1831=73.766/80，1832=78.326/80，1833=99.268/100，1834=99.748/100，1841=179.004/180。当前人力表仍满额，不宣称已证实人力伤亡；也不能宣称本次没有造成游戏损伤。此前GS战斗表为空，现在两场战斗duration23，符合这次异常延长推进期间自然陆战与HP损耗。按不可逆游戏损伤安全条件保守停止一切进一步游戏写入/Post，不再解除暂停；没有尝试回滚内存或读写存档。\n新升格总计7项，清单14表116字段，已验证71，未验证45（12非内存配置/feedback +33内存候选）。SHA256: '''+v['inventory']['sha256']+'''。已读回SHA一致、无BOM。进程pid12948存活，官方pause1，速度槽0即1x，游戏1936-01-02 15:00；计划1执行false，全部已读计划执行false；allow_post=false，闸门文件不存在。\n剩余实质障碍：行军commandlist/full_path仍空，order type/target/eta不能由普通path或movement_progress擅自替代；计划type2未有官方命名、axis/status未验证；补给缺少官方消费链语义/孤立正例；可见敌军缺少FoW门；战斗phase/result/start/end/casualties仍缺对应schema语义，不能把day/duration当时间戳；短缺类仍缺非空官方需求/缺额与影响关联；crisis/invalidated等属推断或缺官方样本；leader unit assignment不再用SetArmyLeader试探。\n注意：t197_final_status.py内置sha_ok只比较历史t197 SHA，t198更新后false是历史pin不匹配，不是D盘损坏。以t198_validation.json的实际SHA/结构计数为准。\n已补input_capture_live.py实际部分导出的plans/combats与own_units参战正例，不输出不存在的false，也不扩大可见敌军范围。\n工具限制记录：用户机没有rg、没有pytest；直接用内置unittest回归，不安装依赖。\n''')
print('FINAL CHECKPOINT',hashlib.sha256((R/'research/t198_checkpoint.md').read_bytes()).hexdigest())
