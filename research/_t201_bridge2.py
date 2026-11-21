from pathlib import Path
exec((Path(__file__).parent/'_t200_start.py').read_text(encoding='utf-8').split('# one opening')[0])
from gamestate import _rtti_name_from_vtable
cs.detail=False
out={}
# Find function pointer references and their actual MSVC owning vtables, without assuming combat class.
for a in(0x1489550,0x1347fd0,0x1348d30):
 hits=[];pos=0
 while True:
  pos=p.data.find(struct.pack('<Q',0x140000000+a),pos+1)
  if pos<0:break
  sec=next((s for s in p.sections if s.raw_ptr<=pos<s.raw_ptr+s.raw_size),None)
  if sec is None:continue
  ra=sec.virtual_address+pos-sec.raw_ptr
  for delta in range(0,0x180,8):
   try:name=_rtti_name_from_vtable(p,ra-delta)
   except Exception:continue
   if name and name.startswith('.?AV'):
    hits.append({'pointer_rva':hex(ra),'vt_rva':hex(ra-delta),'slot':hex(delta),'class':name});break
 out[hex(a)]=hits
# Actual UI object construction and sites touching its category+224.
out['ui_ctor_fc31c0']=clip(0xfc31c0)
text=next(s for s in p.sections if s.name=='.text');seen=set();hits=[];pos=text.raw_ptr
while True:
 pos=p.data.find(bytes.fromhex('24020000'),pos+1)
 if pos<0 or pos>=text.raw_ptr+text.raw_size:break
 at=text.virtual_address+pos-text.raw_ptr;st,en=fn(at)
 if not 0xfc0000<=st<0xfd0000 or st in seen:continue
 seen.add(st);ls=clip(st)
 for line in ls:
  if '0x224]'in line:
   ip=int(line.split()[0],16);hits.append({'at':hex(ip),'fn':hex(st),'asm':line,'context':[s for s in ls if ip-60<=int(s.split()[0],16)<=ip+75]})
out['ui_224_refs']=hits
(R/'research/t201_plan_combat_owners.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
with(R/'research/t201_checkpoint.md').open('a',encoding='utf-8')as f:f.write('''\n## 块2：已找到真实师级补给UI与计划UI所有者（未升格）\nARMY_UNIT_SUPPLY_DESC_BAD/OK位于1744D30，其分支明确调用CArmy主vt+158=CE4F10，数值由CE4CD0给出，buffer值由vt+180=CE4C20给出。CE4CD0完整叶函数：当Army+600>0时，以max(Army+40, Army+610/全局buffer天数)裁剪至[0,100000]；CE4F10对相同组合量与全局阈值比较，但+2F8特殊态直接不判缺补给。与consumer+30=Army+40的继承定位吻合；不能把单一字段默认1当成完整满足率。已避免先前64字节叶函数截断，完整证据见t201_semantic_bridges.json。\nFC9880的两个调用者E733AB/E7645D通过idler虚槽+C8取得对象；新只读槽确认E33D70返回idler+A48；E4ABF0先分配0x328字节、调用FC31C0再存入+A48。继续沿该真实UI对象的+224写点，而非在COrderInstance+224强套枚举。\nCombat1489550确实写+E8=GS小时值减固定epoch、+E0=2后尾调1347FD0，但现有CLandCombat原始头+E0为指针，不能当通用陆战phase/start；正在利用方法指针归属vtable辨别派生类。历史原始头无需重复活体探测。\n库存仍72/44、14表116字段3列，SHA未改；本段到此用量读数26.6%，不作为开段基线。\n''')
