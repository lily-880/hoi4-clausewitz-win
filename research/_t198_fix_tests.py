from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win')
p=R/'research/test_t185_input_combatant_activity.py';s=p.read_text(encoding='utf-8');old='''        raw = INV.read_bytes()
        text = raw.decode("utf-8")
        self.assertIn("| 字段名 | 已验证/未验证 | 说明 |", text)
        self.assertIn("| world.own_units.in_combat | 未验证 |", text)
''';assert s.count(old)==1;s=s.replace(old,'''        # Historical t185 acceptance is pinned below. The live inventory legitimately
        # advances (t198 has nonempty player-involved combat evidence).
''');p.write_text(s,encoding='utf-8')
with (R/'research/t198_checkpoint.md').open('a',encoding='utf-8') as f:f.write('\n离线回归首次发现t198 fake-memory测试的测试数据指针低于reader安全下限，已把假指针移到0x16000（不放宽生产检查）。t185旧测试仍要求实时清单in_combat=未验证，已冻结为其原有t185 evidence assertions，保留116/43/73历史断言，不与t198当前清单混用。\n')
