"""Pure local disassembly CFG; no process APIs, game calls or writes."""
def walk_flow(cs,raw,start,entry=None,max_steps=16384):
 end=start+len(raw);todo=[start if entry is None else entry];seen={};unresolved=[];tails=[];calls=[]
 while todo:
  ip=todo.pop()
  if ip in seen:continue
  if not start<=ip<end:unresolved.append({'address':hex(ip),'reason':'outside window'});continue
  if len(seen)>=max_steps:raise ValueError('CFG step bound')
  i=next(cs.disasm(raw[ip-start:ip-start+15],ip,count=1),None)
  if i is None or ip+i.size>end:unresolved.append({'address':hex(ip),'reason':'decode/end failure'});continue
  seen[ip]=i
  if i.mnemonic.startswith('ret')or i.mnemonic in('int3','ud2'):continue
  if i.mnemonic.startswith('call'):calls.append({'site':hex(ip),'operand':i.op_str})
  if i.mnemonic.startswith('j')or i.mnemonic in('loop','loope','loopne'):
   try:dst=int(i.op_str,0)
   except ValueError:dst=None
   if dst is not None:
    if start<=dst<end:todo.append(dst)
    elif i.mnemonic=='jmp':tails.append({'site':hex(ip),'target':hex(dst)})
    else:unresolved.append({'address':hex(ip),'target':hex(dst),'reason':'conditional target outside window'})
   else:unresolved.append({'address':hex(ip),'reason':'indirect jump','operand':i.op_str})
   if i.mnemonic=='jmp':continue
  todo.append(ip+i.size)
 return {'scope':'direct-control reachability in bounded byte window; calls opaque; no global-write absence claim','window_start':hex(start),'window_size':len(raw),'reachable_instruction_count':len(seen),'unresolved_edges':unresolved,'external_tails':tails,'calls':calls,'asm':[f'{v.address:x} {v.mnemonic} {v.op_str}'for k,v in sorted(seen.items())]}
