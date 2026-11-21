from pathlib import Path
import json,hashlib,collections
D=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');original=D.read_bytes();s=original.decode('utf-8-sig');rows=[]
for line in s.splitlines():
 if line.startswith('| '):
  cells=[x.strip() for x in line.strip().strip('|').split('|')]
  if len(cells)==3 and cells[1] in ('已验证','未验证'):rows.append(cells)
assert len(rows)==116 and len({r[0] for r in rows})==116
pending=[r for r in rows if r[1]=='未验证'];assert len(pending)==95
plans=[('meta.','接口配置/会话','核实当前国家tag来源与暂停位；allow_write/scope只按显式配置合成且标明来源。'),('policy.','玩家配置','校验玩家方针或契约默认配置，不记为活内存证明。'),('world.own_units.template.','已加载营定义','用具名combat_width解析器定位FIXED字段，并对当前四模板逐营求和与复读。'),('world.leaders.','国家人物与将领名册','己方CCountryCharacters正式名册、CCharacter指针连接、具名序列化和跨20将领复读；任职另查组织反向链接。'),('world.own_units.','师动态状态','从CArmy具名序列化/调用点定位当前HP、人力、补给、任务和编成；需要语义与跨对象不变量，空路径不解释为待机。'),('world.visible_units','可见性/情报','定位玩家侧spotted/intel查询和迷雾过滤，禁止把可扫描世界单位导入可见单位。'),('world.army_groups.','编成','审查各国非空CArmyGroup/上级组织实例及成员/司令双向关系，隐藏世界证据不进入玩家输出。'),('world.armies.','编成','追踪CTheatre下正式军级组织和师成员反向引用，区分集团军与CArmy师。'),('world.provinces.','动态地图与已加载定义','以CProvince/CState/CBuilding当前实例及具名字段交叉证明，邻接需边类型/渡河语义，缺建筑不直接填0。'),('world.plans.','计划','检查世界已有计划管理器和具体非空计划类；CFront不能自动当作玩家计划。'),('world.combats.','战斗','检查GS内CCombatManager全世界实例与具名字段，空表不证明师未作战；需要非空对象验收。'),('world.crises.','派生态势','先验证补给/包围/任务失败等基础字段，再按可审计派生规则产生危机，不把未知变成false。'),('world.wars.','外交/战争','定位全局战争关系和参战方当前对象、状态枚举；停火/投降/傀儡分别证明。'),('world.shortages.','资源/派生缺口','读取国家装备库存/需求和CCountryManpower，先证明available/needed含义，再推导缺口和受影响对象。'),('feedback.','接口命令回执账本','仅从本地真实命令回执/采集节拍计算；本任务无写入，不伪造命令或游戏接受结果。')]
audit=[]
for f,_,meaning in pending:
 prefix,category,next_step=next(p for p in plans if f.startswith(p[0]));audit.append({'field':f,'baseline_status':'未验证','meaning':meaning,'dependency_class':category,'next_independent_action':next_step,'user_participation_required_now':False})
Path('research/t165_95_field_dependency_audit.json').write_text(json.dumps({'baseline_unverified':95,'config_is_not_memory_proof':True,'empty_current_sample_is_not_global_blocker':True,'items':audit},ensure_ascii=False,indent=2),encoding='utf-8')
updates={'world.own_units.template.combat_width':'当前四种己方模板由已加载主战营宽度求和的战斗宽度。','world.leaders.leader_id':'当前己方20名陆军将领档案编号，非师军官编号。','world.leaders.name':'当前己方20名陆军将领的人物档案完整显示姓名。','world.leaders.skill':'当前己方20名陆军将领的总等级。','world.leaders.attack':'当前己方20名陆军将领的进攻属性。','world.leaders.defense':'当前己方20名陆军将领的防御属性。','world.leaders.planning':'当前己方20名陆军将领的计划属性。','world.leaders.logistics':'当前己方20名陆军将领的后勤属性。','world.leaders.traits':'当前己方20名陆军将领的完整内部特性名称。','world.provinces.infrastructure':'当前5010省所属州已检出且无损的基础设施等级。'}
new=[];seen=set()
for line in s.splitlines():
 if line.startswith('| '):
  c=[x.strip() for x in line.strip().strip('|').split('|')]
  if c[0] in updates:line='| '+c[0]+' | 已验证 | '+updates[c[0]]+' |';seen.add(c[0])
 new.append(line)
assert seen==set(updates)
newtext='\n'.join(new)+'\n';newbytes=newtext.encode('utf-8')
assert newtext.count('| 字段名 | 已验证/未验证 | 说明 |')==14
for line in newtext.splitlines():
 if line:assert line.startswith('|') and len(line.strip('|').split('|'))==3
assert sum(' | 已验证 | ' in x for x in new)==31 and sum(' | 未验证 | ' in x for x in new)==85
Path('research/t165_态势信息读取能力清单_更新前.md').write_bytes(original)
Path('research/t165_态势信息读取能力清单_修订.md').write_bytes(newbytes)
D.write_bytes(newbytes);back=D.read_bytes();assert back==newbytes;back.decode('utf-8')
manifest={'target':str(D),'sha256':hashlib.sha256(back).hexdigest(),'utf8_readback_equal':True,'tables':14,'columns':3,'fields':116,'verified':31,'unverified':85,'newly_verified_fields':list(updates),'prior_sha256':hashlib.sha256(original).hexdigest()}
Path('research/t165_document_update_verification.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(manifest,ensure_ascii=False,indent=2))
