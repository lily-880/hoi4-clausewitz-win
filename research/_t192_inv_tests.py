from pathlib import Path
for name in ["test_t185_input_combatant_activity.py","test_t186_input_wars.py","test_t187_input_pause.py","test_t188_input_plans.py","test_t189_input_crisis_fow_buildings.py","test_t182_input_combat_order.py","test_t183_input_assigned_combat_command.py","test_t184_input_formation_combat.py"]:
    p = Path("research")/name
    lines = p.read_text(encoding="utf-8").splitlines()
    # print inventory test function
    inside=False
    print("="*20, name)
    for i,l in enumerate(lines,1):
        if l.strip().startswith("def test_inventory") or "INV.read" in l or "hexdigest" in l or "live D" in l:
            inside=True
        if inside:
            print(f"{i:4d}|{l}")
            if l.strip().startswith("def ") and "inventory" not in l:
                break
            if inside and l.strip()=="" and i>0:
                # keep going until next def at class level? 
                pass
        if inside and l.startswith("    def ") and "inventory" not in l:
            break
