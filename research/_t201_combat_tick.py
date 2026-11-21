from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
cs.detail=False
out={}
for a in(0xc0c660,0x1347fd0):
 j=bisect.bisect_right(starts,a)-1;parts=[fns[j]];end=fns[j][1]
 for row in fns[j+1:j+8]:
  if row[0]!=end:break
  raw=p.read_rva(row[2]&~3,4);flags=raw[0]>>3;count=raw[2]
  if not flags&4:break
  chain=struct.unpack('<III',p.read_rva((row[2]&~3)+((4+2*count+3)&~3),12))
  if chain[0]!=a:break
  parts.append(row);end=row[1]
 ls=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in cs.disasm(p.read_rva(a,end-a),a)];(R/f'research/_t201_whole_{a:x}.txt').write_text('\n'.join(ls),encoding='utf-8');out[hex(a)]={'parts':[[hex(v)for v in row]for row in parts],'asm':ls}
(R/'research/t201_combat_hourly_manager.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
