from _t202_common import *
import re
x=Runtime()
try:
 before=x.guard();r=x.reader();out={'land_combat_virtuals':{},'native_stat_functions':{},'live_combatant_record_candidates':[],'plan_geometry_inputs':[]}
 for a in(0x133d6b0,0x147da00,0x1339b00,0x1fa590):out['native_stat_functions'][hex(a)]=x.clip(a)
 for cp in r.array(x.gs+0x268,4096):
  r.require(cp,'CLandCombat');vt=r.q(cp)
  for slot in(0x30,0x68,0x88,0x90,0xc0):
   a=r.q(vt+slot)-x.base
   if hex(a)not in out['land_combat_virtuals']:out['land_combat_virtuals'][hex(a)]={'slot':hex(slot),'function':x.clip(a)}
  for side,off in(('attacker',0x28),('defender',0x30)):
   bp=r.q(cp+off);r.require(bp,'CLandCombatant');records=[]
   for rp in r.array(bp+0x140,256):
    raw=r.exact(rp,32);records.append({'ptr':hex(rp),'raw32':raw.hex(),'handle_at8':list(struct.unpack_from('<II',raw,8)),'integer14':struct.unpack_from('<i',raw,0x14)[0]})
   out['live_combatant_record_candidates'].append({'combat_id':r.i(cp+0x1c),'side':side,'array_140':records,'note':'Candidate records, no manpower/HP label until writer semantics proven.'})
 # New geometry reads for already observed nested instances, never change them.
 seen=set();pending=[]
 for tp in r.array(x.country+0x168,64):
  for gp in r.array(tp+0x80,256):
   for off in(0x98,0xb0,0xc8):pending+=r.array(gp+off,256)
 while pending:
  ip=pending.pop(0)
  if ip in seen:continue
  seen.add(ip);assert len(seen)<=256;r.require(ip,'COrderInstance');raw=r.exact(ip+0x280,16);data,cap,n=struct.unpack('<QII',raw);assert 0<=n<=cap<=4096
  out['plan_geometry_inputs'].append({'id':r.i(ip+0x244),'orders_group_ptr38':hex(r.q(ip+0x38)),'midpoints_header280':raw.hex(),'midpoints_count':n,'coord_268_270_raw':r.exact(ip+0x268,16).hex(),'type_raw':r.i(ip+0x30)})
  for off in(0x1f8,0x2d0):pending+=r.array(ip+off,256)
 r.stable();after=x.guard();assert before==after;out['guard_after']=after;(R/'research/t202_deep_semantics.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('LAND_VIRTUALS',[(a,d['slot'],len(d['function']['asm']))for a,d in out['land_combat_virtuals'].items()]);print('NATIVE_STAT_FUNCTIONS',[(a,len(d['asm']))for a,d in out['native_stat_functions'].items()]);print('LIVE_RECORDS',json.dumps(out['live_combatant_record_candidates'],indent=2));print('PLAN_GEOMETRY',json.dumps(out['plan_geometry_inputs'],indent=2))
 with(R/'research/t202_checkpoint.md').open('a',encoding='utf-8')as f:f.write('''\n## 块2：目标函数桥接、排除跨类猜测\n147E600不是直接统计字段writer，而是按双方真实CLandCombatant虚表依次调用B0、98、70、100槽；活体绑定对应133F5B0、13480E0、1347CC0、134BF50，已展开真实回调而非猜offset。134BF50把对方E8/100/118单元列表按国家聚合计数，并遍历+140候选记录的+8句柄、+14整数；尚未把此整数称人力伤亡，继续追写入者。\n133A150仅构造0xD8字节普通陆战派生体，+D0=-1，不自带已证明start；新直接调用者C0B8D0是正常创建链、C0DB60有token分流及序列化入口，不能把读档解析分支当正常新战创建。这里只读代码，不调用解析、不读取存档。C0B8D0会调用1FA590后交2283C60管理ID，须辨别ID分配与时间，不能见date形似数值就升格started_at。\nFCF8F0的UI2/3/4分支明确把实例+70路径作为第5参数、实例作为第6参数传12E6E20，r9为0；渲染器另有r9非空的双线几何分支。实际axis是否独立字段仍须区分输入顶点与派生箭头，不能将同一+70重复命名axis。现存子4/3继续作为非空语义对照。\n新读取嵌套实例几何和当前四侧+140候选记录见t202_deep_semantics.json，均为有实质新调用链的针对性只读采样，未制造时间样本。\n''')
finally:x.close()
