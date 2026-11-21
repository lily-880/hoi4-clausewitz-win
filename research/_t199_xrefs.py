exec(open(__file__.replace('_t199_xrefs.py','_t199_inspect.py'),encoding='utf-8').read().split('c=json.loads')[0])
import re
ss=json.loads((R/'research/t199_named_strings.json').read_text())
chosen=[x for x in ss if x['text'].startswith('ORDER_') or any(k in x['text'] for k in ('GetSupply','IsInSupply','CombatDuration','LandCombat::','CombatManager::','SupplyRatio','SupplyStatus','SupplySatisfaction','HasEnded','HasFinished'))]
print('CHOSEN',json.dumps(chosen,indent=2))
# xrefs for exact plan enum2/official supply getters/lifecycle strings
targets={int(x['rva'],16):x['text'] for x in chosen if not x['text'].startswith('ORDER_') or x['text']in('ORDER_FRONT','ORDER_FRONTLINE','ORDER_DEFEND','ORDER_DEFENSIVE')}
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
pdata=next(s for s in p.sections if s.name=='.pdata');fns=list(struct.iter_unpack('<III',p.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size//12*12]))
refs=[]
for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',p.data):
 i=m.start();a=rv(i)
 if not a:continue
 target=a+7+struct.unpack_from('<i',p.data,i+3)[0]
 if target not in targets:continue
 fn=next(((s,e)for s,e,u in fns if s<=a<e),None)
 rec={'at':hex(a),'text':targets[target],'fn':hex(fn[0]) if fn else None}
 if fn:
  rec['asm']=[f'{ii.address:x} {ii.mnemonic} {ii.op_str}' for ii in cs.disasm(p.read_rva(max(fn[0],a-80),min(fn[1]-max(fn[0],a-80),200)),max(fn[0],a-80))]
 refs.append(rec)
(R/'research/t199_named_xrefs.json').write_text(json.dumps(refs,indent=2),encoding='utf-8');print('XREFS',json.dumps(refs,indent=2))
