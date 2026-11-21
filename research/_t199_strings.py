exec(open(__file__.replace('_t199_strings.py','_t199_inspect.py'),encoding='utf-8').read().split('c=json.loads')[0])
import re
terms=(b'ORDER_',b'GetSupply',b'IsInSupply',b'GetCombat',b'CombatDuration',b'LandCombat::',b'CombatManager::',b'SupplyRatio',b'SupplyStatus',b'SupplySatisfaction',b'HasEnded',b'HasFinished')
def rv(off):
 for s in p.sections:
  if s.raw_ptr<=off<s.raw_ptr+s.raw_size:return s.virtual_address+off-s.raw_ptr
out=[]
for m in re.finditer(rb'[\x20-\x7e]{5,}',p.data):
 text=m.group()
 if any(t in text for t in terms):out.append({'rva':hex(rv(m.start())or 0),'text':text.decode()[:400]})
(R/'research/t199_named_strings.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
# full concise prior supply evidence
print('SUPPLY', (R/'research/t185_supply_consumer.json').read_text(encoding='utf-8'))
