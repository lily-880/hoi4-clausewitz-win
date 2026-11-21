from _t204_common import *
import re
x=Runtime()
try:
 b=x.guard();out={'token3750_sites':[],'loss_literals':[],'functions':{hex(a):x.clip(a)for a in(0xd3f020,0xd3f4d0,0xd38c90,0x133e700)}};lo,n=x.sections['.text'];raw=x.code(lo,n)
 for opcode in range(0xb8,0xc0):
  key=bytes([opcode])+struct.pack('<I',0x3750);p=0
  while True:
   p=raw.find(key,p)
   if p<0:break
   start=p-7 if p>=7 and raw[p-6]==0x8d and raw[p-5]&0xc7==5 else p;window=raw[start:p+90];ls=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in x.cs.disasm(window,lo+start)];out['token3750_sites'].append({'site':hex(lo+p),'asm':ls});p+=1
 rv,nr=x.sections['.rdata'];rd=x.code(rv,nr)
 for m in re.finditer(rb'[A-Za-z_]{0,40}(?:manpower|casualt)[A-Za-z_]{0,50}\x00',rd,re.I):
  s=m.group()[:-1].decode();out['loss_literals'].append({'rva':hex(rv+m.start()),'text':s})
 assert x.guard()==b;(R/'research/t204_stats_loss_semantics.json').write_text(json.dumps(out,indent=2),encoding='utf8');print('TOKEN SITES',json.dumps(out['token3750_sites'],indent=2));print('LOWERCASE',json.dumps([z for z in out['loss_literals']if z['text'].islower()],indent=2));print('FINALIZERS',{k:v['asm'][:18]for k,v in out['functions'].items()})
finally:x.close()
