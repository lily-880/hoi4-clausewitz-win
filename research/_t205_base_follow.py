from _t205_common import *
x=Runtime()
try:
 g=x.guard();out={'supply_base_parser':x.clip(0xf46e30),'orders_group_getter':x.clip(0x34c290),'combat_method20':x.clip(0x147eb20),'combat_methodc8':x.clip(0x147db50),'combat_method38':x.clip(0x133e650),'other_v70_sites':[]};lo=0x1330000;raw=x.code(lo,0x1d000)
 for lo,n in((0x1330000,0x1d000),(0x1470000,0x20000)):
  raw=x.code(lo,n)
  for op in list(range(0x50,0x58))+list(range(0x60,0x68)):
   key=bytes([0xff,op,0x70]);p=0
   while True:
    p=raw.find(key,p)
    if p<0:break
    if lo+p in(0x147e668,0x147e67f):p+=1;continue
    f=x.clip(lo+p);ks=[k for k,s in enumerate(f['asm'])if s.startswith(f'{lo+p:x} ')and' + 0x70]'in s]
    for k in ks:out['other_v70_sites'].append({'site':hex(lo+p),'function':f['start'],'context':f['asm'][max(0,k-13):k+13]})
    p+=1
 assert x.guard()==g;(R/'research/t205_supply_base_and_combat_dispatch.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('V70',json.dumps(out['other_v70_sites'],indent=2))
 for k in('supply_base_parser','orders_group_getter','combat_method20','combat_method38'):print(k,'\n'.join(out[k]['asm']))
finally:x.close()
