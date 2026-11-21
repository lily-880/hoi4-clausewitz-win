# C-authority research/docs recovery only. No game process access.
from pathlib import Path
import json,hashlib,zipfile,datetime
Q=Path(__file__).resolve().parent;A=Path(r'C:\Users\Lenovo\Documents\钢四陆军总司令');H=lambda b:hashlib.sha256(b).hexdigest()
parent=json.loads((Q/'t235_authority_manifest.json').read_text(encoding='utf-8'))
for e in parent['entries']:assert H((A/e['path']).read_bytes())==e['sha256']
payload=Q/'t237_reconcile_payload.zip';assert H(payload.read_bytes())=='eaca006686236ce529a3a7667c3a3945a2f2d563510a1b062d0214e81e78a55c'
with zipfile.ZipFile(payload) as z:
 m=json.loads(z.read('reconcile_manifest.json'));assert len(m['entries'])==26
 for e in m['entries']:
  name=e['name'];assert Path(name).name==name;raw=z.read(name);assert len(raw)==e['size'] and H(raw)==e['sha256']
  p=A/'records'/name
  if p.exists():assert p.read_bytes()==raw
  p.write_bytes(raw)
  # Preserve failed/stopped sources byte-for-byte, also restore evidence to research.
  rp=Q/name
  if rp.exists():assert rp.read_bytes()==raw
  rp.write_bytes(raw)
receipt=dict(at_est=datetime.datetime.now().astimezone().isoformat(),prior_authority_records=parent['record_count'],reconciled_records=26,pending_24_authority_copies_resolved=True,two_laptop_helper_jsons_retrieved=True,pending_checkpoint_audit_unchanged=True,terminal_game_recheck=False,promotions=[],inventory_sha256=H((A/'态势信息读取能力清单.md').read_bytes()),entries=m['entries'])
assert receipt['inventory_sha256']=='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode();(Q/'t237_reconcile_receipt.json').write_bytes(raw);(A/'records'/'t237_reconcile_receipt.json').write_bytes(raw)
assert b'## t237 recovery' not in (A/'README.md').read_bytes()
with (A/'README.md').open('ab') as f:f.write(('\r\n\r\n## t237 recovery — t236 pending copies resolved\r\n2026-11-21 EST: restored26 records (24pending +2helperJSONs), preserving prior BOX_PENDING_C audit byte-for-byte. Inventory87/29 SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3 unchanged. No new game access or terminal recheck claimed by this recovery; see records/t237_reconcile_receipt.json.\r\n').encode('utf-8'))
files=[A/'README.md',A/'态势信息读取能力清单.md']+sorted((A/'records').glob('*'))
manifest=dict(at_est=receipt['at_est'],authority=str(A),record_count=len(files)-2,entries=[dict(path=p.relative_to(A).as_posix(),size=p.stat().st_size,sha256=H(p.read_bytes())) for p in files]);mp=Q/'t237_reconciled_authority_manifest.json';mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
out=Q/'t237_reconciled_authority.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'authority/'+p.relative_to(A).as_posix())
 z.write(mp,mp.name)
print(json.dumps(dict(records=manifest['record_count'],files=len(files),archive=str(out),size=out.stat().st_size,sha256=H(out.read_bytes())),indent=2))
