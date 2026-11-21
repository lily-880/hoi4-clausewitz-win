from pathlib import Path
# t179 test + inventory line + existing test runner
print("=== test_t179 ===")
p=Path("research/test_t179_input_formulas_and_77.py")
print(p.read_text(encoding="utf-8"))
