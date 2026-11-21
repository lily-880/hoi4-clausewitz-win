"""Bounded read-only candidate probe. NOT demanded/deficit contract proof."""
import sys,json,struct,hashlib
from pathlib import Path
sys.path.insert(0,'research');from t156_objects import P,cls
sys.path.insert(0,'calling')
from input_loaded_fields import LoadedReader
from gamestate import resolve_player_country,detect_session
try:
 profile=json.loads(Path('calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8'))
 with open(P.image_path,'rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest().upper()
 assert digest==profile['exe_sha256']
 r=LoadedReader(P.read,cls);gs=r.q(P.base+0x33dd6b0);assert r.i(gs+0x4bc)==0
 resolution=resolve_player_country(P,gs);assert resolution['ok'];co=int(resolution['country_ptr'],16);header=r.exact(gs+0x468,0xc0)
 rs=r.q(co+0xf78);r.require(rs,'CReinforcementStatus');groups=r.array(rs+0x20,64)
 out={'pid':P.pid,'version':profile['game_version'],'country_index':r.i(co+8),'need_not_accepted':True,'groups':[],'coverage':'At most4 groups and8 requests/group; candidate pools only, NOT a complete country demand or unit attribution'}
 for gp in groups[:4]:
  r.require(gp,'CArmyReinforcementRequests');entries=r.array(gp+0x28,256);g={'class':cls(gp),'count':len(entries),'samples':[]}
  for ep in entries[:8]:
   r.require(ep,'CReinforcementRequest');row={'ptr':hex(ep),'current':[],'required':[]}
   for key,pool,stride,expected in [('current',ep+0x38,24,'CEquipmentVariantPool'),('required',ep+0x78,16,'CEquipmentArcheTypePool')]:
    r.require(pool,expected);types=r.array(pool+8,64,stride);data=r.q(pool+8)
    for j,tp in enumerate(types):
     r.require(tp,'CEquipmentType');quantity=struct.unpack('<q',r.exact(data+j*stride+(16 if stride==24 else 8),8))[0];row[key].append({'type':r.string(tp+0x18),'amount_raw':quantity})
   g['samples'].append(row)
  out['groups'].append(g)
 out['stable_reads']=r.stable();Path('research/t169_reinforcement_probe_repeat.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
finally:P.close()
