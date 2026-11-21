import json
from pathlib import Path
d=json.loads(Path('research/t191_live_units.json').read_text(encoding='utf-8'))
print('pid', d.get('pid'), 'tag', d.get('tag'), 'units', d.get('unit_count'), 'country', d.get('country'), 'gs', d.get('gs'))
print('first unit', json.dumps(d['units'][0], ensure_ascii=False)[:500] if d.get('units') else None)
print('last unit', json.dumps(d['units'][-1], ensure_ascii=False)[:400] if d.get('units') else None)
# controller fields of first occupied province
pids=set(u['province_id'] for u in d.get('units') or [])
print('occupied', sorted(pids))
for pid in list(sorted(pids))[:3]:
    info=d['provinces'].get(str(pid)) or d['provinces'].get(pid)
    if info:
        keys=['province_id','controller','owner','controller_class','controller_area','controller_backlinks','controller_index_hits','land_neighbors']
        print('prov', {k:info.get(k) for k in keys})
# dump one area probe if present
print('province key types', type(next(iter(d['provinces']))))
print('n provinces', len(d['provinces']))
