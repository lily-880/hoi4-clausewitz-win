# Machine-dependent read-only live-session rebind; never game writes/calls/capture.
import sys,json,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q));from _t207_session import Runtime,country_tag
H=lambda b:hashlib.sha256(b).hexdigest();prev=json.loads((Q/'t235_final_seal.json').read_text(encoding='utf-8'));pins=json.loads((Q/'t237_prior_all_native_pins.json').read_text(encoding='utf-8'));assert len(pins)==135
rt=Runtime()
try:
 before=rt.guard();version=rt.code(0x2795083,48).split(b'\0')[0].decode();r=rt.reader();tag=country_tag(r,rt.gs,rt.index,rt.country)
 safe=before['pause']==1 and before['speed_slot']==0 and not any(before['markers'].values()) and version=='1.19.5.0.7c6c' and tag=='SOV'
 out=dict(at_est=datetime.datetime.now().astimezone().isoformat(),before=before,version=version,country_tag=tag,safe=safe,roots_fresh=True)
 if safe:
  for name,h in prev['production_hashes'].items():assert H((Q.parent/name).read_bytes())==h
  for va,n in [(0x147c330,2048),(0xcec2e0,4096)]:assert H(rt.code(va,n))==prev['native_controls'][hex(va)]
  for p in pins.values():assert H(rt.code(int(p['window_start'],16),p['window_size']))==p['sha256']
  out.update(rechecked_prior_native_windows=len(pins),production_hashes=prev['production_hashes'],native_controls=prev['native_controls'],production_baseline_fields=51,stable_dependencies=r.stable())
 out['after']=rt.guard();out['safe']=safe and out['before']==out['after'];(Q/'t237_fresh_guard.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2));assert out['safe']
finally:rt.close()
