from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
cs.detail=False
out={}
for a in (0xce4f10,0xce4c20,0xce4cd0,0x1347fd0,0x1348d30,0x147c240,0x1489550,0xe4abf0,0xe32250):
 if a in(0xce4f10,0xce4c20,0xce4cd0):
  ls=[]
  for i in cs.disasm(p.read_rva(a,512),a):
   if i.mnemonic=='int3':break
   ls.append(f'{i.address:x} {i.mnemonic} {i.op_str}')
 else:ls=clip(a)
 out[hex(a)]=ls if a!=0x1489550 else ls[:55]
snap=json.loads((R/'research/t198_current_snapshot.json').read_text());out['historical_primary_f0']={c['ptr']:{hex(k):struct.unpack_from('<I',bytes.fromhex(c['head']),k)[0]for k in(0x30,0x34,0x40,0x44,0xe0,0xe8,0xf0,0xf4,0xf8,0xfc)}for c in snap['combats']}
(R/'research/t201_semantic_bridges.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
