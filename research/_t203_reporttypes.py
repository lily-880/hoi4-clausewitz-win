from _t203_common import *
from _t203_delivery_reader import tag_index
x=Runtime()
try:
 b=x.guard();r=x.reader();out={'constructor_classes':{},'existing_country_log':None}
 for va in(0x29d9f40,0x29da210):
  col=x.q(x.base+va-8);sig,off,cd,td=struct.unpack('<IIII',x.pr.read(col,16));assert sig==1;out['constructor_classes'][hex(va)]=x.code(td+0x10,160).split(b'\0')[0].decode('ascii')
 tag=r.i(x.country+8);idx=tag_index(r,x.gs,tag);tab=r.q(x.gs+0x880)
 if tab:
  root=r.q(tab+idx*8);out['existing_country_log']={'country_tag':tag,'country_index':idx,'root':hex(root)}
  if root:
   out['existing_country_log']['class']=x.cls(root);records=r.array(root+8,4096);out['existing_country_log']['record_count']=len(records);out['existing_country_log']['records']=[]
   for p in records:
    row={'ptr':hex(p),'class':x.cls(p),'monthly_people_records':[]}
    for q in r.array(p+0x98,4096):row['monthly_people_records'].append({'ptr':hex(q),'class':x.cls(q),'date_encoded':r.i(q+0x18),'raw_counts_28_2c_30':list(struct.unpack('<iii',r.exact(q+0x28,12)))})
    out['existing_country_log']['records'].append(row)
 r.stable();assert x.guard()==b;out['schema_emission']=False;out['guard_after']=b;(R/'research/t203_real_people_report_types_live.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out,indent=2))
finally:x.close()
