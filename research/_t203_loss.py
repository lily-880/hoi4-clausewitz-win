from _t203_common import *
x=Runtime()
try:
 before=x.guard();out={'functions':{},'callers':[]}
 for a in(0xcc77d0,0xcc6720,0xd7abc0,0xd7b240):out['functions'][hex(a)]=x.clip(a)
 va,n=x.sections['.text'];raw=x.code(va,n);p=0
 while True:
  p=raw.find(b'\xe8',p)
  if p<0 or p+5>len(raw):break
  dst=va+p+5+struct.unpack_from('<i',raw,p+1)[0]
  if dst in(0xcc77d0,0xcc6720):
   f=x.clip(va+p);key=f'{va+p:x} call {hex(dst)}'
   if key in f['asm']:
    k=f['asm'].index(key);out['callers'].append({'site':hex(va+p),'target':hex(dst),'function':f['start'],'context':f['asm'][max(0,k-20):k+18]})
  p+=1
 out['guard_after']=x.guard();assert before==out['guard_after'];(R/'research/t203_real_loss_chain.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
 with(R/'research/t203_checkpoint.md').open('a',encoding='utf-8')as f:f.write('\n## 块2：扣除性质和encircled官方文案桥\nC4A420由C4C200的HQ/OrdersGroup流程调用；它的CC6BF0返回值是本次实际从师CArmyManpower当前表提取的人数，随即交19C9A20加到部署对象+88。19C9AC0返回max(+8C-+88,0)剩余需求；19C9BC0返回+88/+8C进度，1755D90用DEPLOYING_HQ_PROGRESS_MANPOWER显示它。当前两个真实OrdersGroup+188均空，未制造HQ部署样本。该链已排除为普通战斗累计伤亡，不能把需求缺口、本次抽调、部署已收集量、累计伤亡互换。\n发现更直接的人力扣除链CC77D0：逐国家从表提取fraction数量，按stat+E8算回池部分，剩余记D7ABC0/D7B240统计，再通过CC7550写回old-removed并返回本次removed总人数。其战斗归属和累计范围继续追调用者，不能仅因出现统计writer就填战斗casualties。\n配送消费者159FB30仅在REQUESTED_REINFORCEMENT_DELIVERING_TO与...BLOCKED之间切文案；15A6E40把同一布尔值传15A6510构建补充配送tooltip。本段另发现175D940的change_template_icon/divisions更新路径：E64C50=false明确在175DC38写按钮原因4；1739900原因4使用CHANGE_TEMPLATE_DISABLED_ENCIRCLED。这比possibly cut off文本更强，但继续核实读对象、图依赖与真实分支，尚不凭该文本直接升格。\n21真实师省份+D0的RTTI均CControllerArea，而非此前候选统称supply area；当前同一area，5师+2E=0、16师+2E=1。+2F8均0。已纠正类身份，不能将地区指针当省份/父计划。区域/可达图静态函数存在.pdata分段；EEF530先前29/40行均非完整函数，本段用有界可达CFG补全至103指令，所有边已解析，明确其为全局海军基地映射存在性检查；不把被截断片段称完整证明。\n原清单本地74/42，D最后72/44未同步；0游戏写/0Post/0远程调用，暂停与tick均不变。\n')
 print('FUNCTIONS',[(a,len(v['asm']))for a,v in out['functions'].items()]);print('CALLERS',json.dumps(out['callers'],indent=2))
finally:x.close()
