from pathlib import Path
import json,hashlib
p=Path('research/t205_checkpoint.md');s=p.read_text(encoding='utf8');assert '## Block3'not in s;p.write_text(s+Path('research/t205_block3.md').read_text(encoding='utf8'),encoding='utf8')
p=Path('research/t205_ordinary_battle_close_lifetime.json');d=json.loads(p.read_text(encoding='utf8'));d['result_dispatch']=d.pop('attacker_setter');d['metadata_correction']='D3CD30 reads total_damage/win and forwards results, not a direct attacker/win flag setter';p.write_text(json.dumps(d,indent=2),encoding='utf8')
p=Path('research/_t205_close_lifetime.py');p.write_text(p.read_text(encoding='utf8').replace('attacker_setter','result_dispatch'),encoding='utf8')
d=json.loads(Path('research/t204_promotions_pending_inventory.json').read_text(encoding='utf8'));d['t205_new_promotions']=[];d['t205_note']='Native lifecycle/keyword evidence only. Existing t201 two rows pending; no D access or synchronization; 14/116/3 unchanged.';Path('research/t205_promotions_pending_inventory.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8');print('BLOCK3_READBACK_SHA',hashlib.sha256(Path('research/t205_checkpoint.md').read_bytes()).hexdigest())
