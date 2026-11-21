from pathlib import Path
p=Path('research/test_t179_input_formulas_and_77.py')
t=p.read_text(encoding='utf-8')
old="self.assertIn('template+0x120 minus CArmy+0x348', f['need']['unit_remaining'])"
new="self.assertIn('CReferencedDivisionTemplate+0x120 minus CArmy+0x348', f['need']['unit_remaining'])"
if old not in t:
    raise SystemExit('pattern not found')
p.write_text(t.replace(old,new),encoding='utf-8')
print('patched')
