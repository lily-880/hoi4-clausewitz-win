from pathlib import Path
import json
# terminal output may be huge; extract from saved json instead
p=Path('research/t191_live_units.json')
d=json.loads(p.read_text(encoding='utf-8'))
keys=['ok','process_pid','pid_matches_expected','gs_matches','co_matches','tag','player_index','gs','country','unit_count','handle_types','unit_ids','gs_combats','controller_map_counts','candidate_count']
print(json.dumps({k:d.get(k) for k in keys}, indent=2, ensure_ascii=False))
print('--- area_probe ---')
print(json.dumps(d.get('area_probe'), indent=2, ensure_ascii=False)[:4000])
print('--- occupied ---')
print(json.dumps(d.get('occupied_summary'), indent=2, ensure_ascii=False))
print('--- top8 ---')
print(json.dumps((d.get('candidates_top') or [])[:8], indent=2, ensure_ascii=False))
