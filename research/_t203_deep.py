from _t203_common import *
x=Runtime()
try:
 before=x.guard();out={'flow_windows':{},'callers':[],'hq_ratios':{}}
 for a,n in((0xeef530,0x400),(0xcc68c0,0x400)):
  raw=x.code(a,n);ins={i.address:i for i in x.cs.disasm(raw,a)};todo=[a];seen=set();unresolved=[]
  while todo:
   ip=todo.pop()
   if ip in seen:continue
   if not a<=ip<a+n or ip not in ins:unresolved.append(hex(ip));continue
   seen.add(ip);assert len(seen)<=16384;i=ins[ip]
   if i.mnemonic.startswith('ret')or i.mnemonic=='int3':continue
   if i.mnemonic.startswith('j'):
    if i.op_str.startswith('0x'):todo.append(int(i.op_str,16))
    else:unresolved.append(f'{ip:x} indirect {i.op_str}')
    if i.mnemonic=='jmp':continue
   todo.append(ip+i.size)
  lines=[f'{ins[ip].address:x} {ins[ip].mnemonic} {ins[ip].op_str}'for ip in sorted(seen)];(R/f'research/_t203_flow_{a:x}.txt').write_text('\n'.join(lines),encoding='utf-8');out['flow_windows'][hex(a)]={'window_size':n,'window_sha256':hashlib.sha256(raw).hexdigest(),'reachable_instruction_count':len(lines),'unresolved_edges':unresolved,'asm':lines}
 for a in(0x19c9bc0,0x19c9b60):out['hq_ratios'][hex(a)]=x.clip(a)
 va,n=x.sections['.text'];raw=x.code(va,n);p=0
 while True:
  p=raw.find(b'\xe8',p)
  if p<0 or p+5>len(raw):break
  dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
  if dst in(0xcc68c0,0xcc7550):
   f=x.clip(va+p);key=f'{va+p:x} call {hex(dst)}'
   if key in f['asm']:
    k=f['asm'].index(key);out['callers'].append({'site':hex(va+p),'target':hex(dst),'function':f['start'],'context':f['asm'][max(0,k-18):k+14]})
  p+=1
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t203_true_manpower_delivery_flow.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('FLOW',[(a,d['reachable_instruction_count'],d['unresolved_edges'])for a,d in out['flow_windows'].items()]);print('HQ_RATIO',[(a,d['asm'])for a,d in out['hq_ratios'].items()]);print('CALLERS',json.dumps(out['callers'],indent=2))
finally:x.close()
