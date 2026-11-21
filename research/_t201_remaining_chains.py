from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
cs.detail=False
text=next(s for s in p.sections if s.name=='.text')
def functions_with_disp(disp,lo,hi):
 pos=text.raw_ptr;seen=set()
 while True:
  pos=p.data.find(struct.pack('<I',disp),pos+1)
  if pos<0 or pos>=text.raw_ptr+text.raw_size:break
  at=text.virtual_address+pos-text.raw_ptr;st,en=fn(at)
  if not lo<=st<hi or st in seen:continue
  seen.add(st);yield st,list(cs.disasm(p.read_rva(st,en-st),st))
def context(ls,ip,pre=60,post=75):return[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in ls if ip-pre<=i.address<=ip+post]
out={'new_ui_category_refs':[],'order_fallback_ui_refs':[],'combat_scheduler_candidates':[]}
for st,ls in functions_with_disp(0x224,0xfd0000,0xfe0000):
 for i in ls:
  if '0x224]'in i.op_str:out['new_ui_category_refs'].append({'fn':hex(st),'at':hex(i.address),'asm':i.mnemonic+' '+i.op_str,'context':context(ls,i.address)})
for st,ls in functions_with_disp(0x298,0xfc0000,0xfe0000):
 for i in ls:
  if '0x298]'in i.op_str:out['order_fallback_ui_refs'].append({'fn':hex(st),'at':hex(i.address),'asm':i.mnemonic+' '+i.op_str,'context':context(ls,i.address)})
for st,ls in functions_with_disp(0x268,0xe00000,0x1b00000):
 arr=[i for i in ls if '0x268]'in i.op_str];calls=[i for i in ls if i.mnemonic=='call'and any(s in i.op_str for s in('+ 0x78]','+ 0x80]'))]
 if not arr or not calls:continue
 out['combat_scheduler_candidates'].append({'fn':hex(st),'array_refs':[context(ls,i.address,50,70)for i in arr],'virtual_calls':[context(ls,i.address,65,35)for i in calls]})
# Known ordinary timers, include first unwind-fragment beyond 1347FE6.
out['ordinary_timer_full']=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in cs.disasm(p.read_rva(0x1347fd0,0x130),0x1347fd0)]
(R/'research/t201_remaining_static_chains.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('UI224',json.dumps(out['new_ui_category_refs'],indent=2));print('FALLBACK_UI',json.dumps(out['order_fallback_ui_refs'],indent=2));print('SCHEDULER_FUNCTIONS',[x['fn']for x in out['combat_scheduler_candidates']]);print('SCHEDULER_DATA',json.dumps(out['combat_scheduler_candidates'],indent=2))
