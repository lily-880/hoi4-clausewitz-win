exec(open(__file__.replace('_t200_supply.py','_t200_start.py'),encoding='utf-8').read().split('# one opening')[0])
# No process attachment here. Compare base/derived secondary supply consumer methods.
out={}
for tag,vt in(('CSupplyConsumer',0x29cfa58),('CArmy_secondary_supply',0x29d6f78)):
 arr=[]
 for j in range(40):
  q=struct.unpack('<Q',p.read_rva(vt+8*j,8))[0];a=q-0x140000000
  if not 0<a<0x2700000:break
  bounds=fn(a);text=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in cs.disasm(p.read_rva(a,48),a)]
  arr.append({'slot':j,'rva':hex(a),'head':text[:7]})
  if 0xf40000<=a<0xf60000 or tag=='CArmy_secondary_supply'and any('sub rcx,'in x or 'lea rcx,'in x for x in text[:3]):clip(a)
 out[tag]=arr
# CArmy supplied serializer: save call graph base-writing evidence
lines=clip(0xced2e0);out['CArmy_serializer_calls']=[l for l in lines if 'call 'in l][:20]
lines=(R/'research/_t200_clip_fc9880.txt').read_text().splitlines();out['plan_tooltip_this_trace']=lines[:65]+[x for x in lines if 0xfca100<=int(x.split()[0],16)<=0xfca185]
(R/'research/t200_supply_virtual_map.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
