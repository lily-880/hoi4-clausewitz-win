from _t202_common import *
from jsonschema import Draft202012Validator
from datetime import datetime,timezone,timedelta
import config
x=Runtime()
try:
 before=x.guard();assert not config.allow_post()and not config.allow_write();r=x.reader();plans,ev=own_plans(r,x.country);r.stable();after=x.guard();assert before==after
 old=[];schema=json.loads((R/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'))
 for label in('a','b'):
  p=R/f'research/t201_full_capture_recursive_{label}.json';d=json.loads(p.read_text(encoding='utf-8'));errors=list(Draft202012Validator(schema).iter_errors(d['observation']));assert not d['complete_input']and len(errors)==52 and all(e.validator=='required'for e in errors);old.append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'schema_error_count':len(errors),'all_errors_required':True,'complete_input':False,'entity_list_counts':{k:len(v)for k,v in d['observation']['world'].items()if isinstance(v,list)}})
 tests=json.loads((R/'research/t202_tests.json').read_text(encoding='utf-8'));assert tests['passed']and tests['tests_run']==66
 out={'created_at_est':datetime.now(timezone(timedelta(hours=-5))).isoformat(),'before':before,'after':after,'official_pause':True,'allow_post':config.allow_post(),'allow_write':config.allow_write(),'markers':{n:(R/'research'/n).exists()for n in('safe_land_tool_gate.OPEN','strategic_only_tool_gate.OPEN')},'post_calls':0,'game_writes':0,'remote_calls':0,'D_file_accesses_this_block':0,'save_accesses':0,'commits_or_pushes':0,'fresh_research_plan_capture':{'scope':'Narrow read-only research sampler, NOT production full input capture; file executable SHA not re-read and production fingerprint gate not bypassed','plans':plans,'evidence':ev},'production_capture_rerun':False,'production_capture_not_rerun_reason':'Its required disk executable SHA/PE read would touch D. No mocking or disabling that gate. Existing exports revalidated offline instead.','existing_full_exports_revalidated_offline':old,'tests':tests,'inventory':{'tables':14,'fields':116,'columns':3,'local_proven':74,'local_unverified':42,'remaining_memory':30,'remaining_nonmemory':12,'new_promotions_t202':0,'D_last_verified':72,'D_last_unverified':44,'D_last_known_sha256':'4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a','D_current_sha256':None,'synced':False},'reader_sha256':hashlib.sha256((R/'calling/input_loaded_fields.py').read_bytes()).hexdigest()}
 (R/'research/t202_readonly_acceptance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 with(R/'research/t202_checkpoint.md').open('a',encoding='utf-8')as f:f.write("""
## 块4：真正人力支线、回归与只读capture验收
另沿已证CArmyManpower+8当前表的真实扣除CC6BF0->CC6C40追调用者，而不是拿HP损耗改称人力。新的加载代码直接call列表中CC6BF0仅C4A420函数内C4B0D4一处（this明确Army+3D0）；CC6C40另有DF3FC0/107EBC0/107ED40调用者。C4A420是延迟队列/批处理长函数，尚未绑定为战斗伤亡写入器。已展开后续可继续，不把它统称损耗。
新只读采样14个现存交战师的真实CArmyManpower，当前人数均等于各自engine_need_total（4000/6000/6300/6600）；这不能推断战斗零伤亡，也不等于战斗累计伤亡账本，因为补充/转移/生效时点尚未闭合。证据t202_manpower_removal_chain.json。HP/org正损耗样本与人力来源明确分离。
新增12项边界回归，连既有54项共66项全部通过；t202_tests.log/json保存真实输出。涵盖真实双线关联、+38类型、栈mode与实例偏移、航空/战术误认、HP/org真实虚槽、ID非时间、出界虚槽候选驳回、只读API约束，以及旧full export独立schema重验52 required缺口。
新t202_readonly_acceptance.json前后官方暂停/日期/6实例false一致，actual config.allow_post=false、allow_write=false，两个marker均检查；仅新增窄范围只读research plan capture，不冒称production full capture。完整生产capture本段未重跑，因为其必需的exe磁盘SHA/PE读取在D盘；没有模拟指纹、没有拆掉闸门。t201两份完整导出仅离线重验，仍complete_input=false，52项required缺失，绝不能报告完整通过。
本地证据74/42、剩内存30+非内存12，新升格0；D最后72/44与旧SHA仅历史已知，本段未读写/同步D，当前D SHA未知。t202 pending补丁仍仅t201两条供给status行、applied=false，14表116字段3列规则不变。
## 已落盘但未穷尽的后续目标
1. 12E1970/12E6E20现已明确双线与+1E0关联；继续目标线与派生箭头的语义映射，不能把同一顶点线重复填axis。type2仍有fallback0/1分流，schema无fallback枚举，不能一刀切命名。
2. 1343100->CEC2E0已确定HP/org；真正manpower扣除CC6BF0唯一直接调用者C4A420，另沿CArmyManpower当前表writer/替换与国家损失统计的调用链继续；不制造损耗样本。普通start/end仍需精确创建与首hour/结束生命周期证据，不用边境战字段。
3. E64C50已证配送连通性：26调用者中159FB30/15A6E40/15A96E0和1755D90/175D940为尚未深查的UI/状态链；需绑定具体文案及原因码4生产者。不能将possibly cut off直接当isolated，也不能用已驳回的CTemplateChanger+218越表候选。
4. 暂停故障仍仅离线历史分析；底层队列/对象生命周期因缺失败payload/执行时点字节仍未全明。硬禁历史脚本不运行、不import。
没有宣布整体任务穷尽，以上是可继续的新函数级线索。本段状态依然PID12948，base7FF7A91C0000，官方暂停1、speed0、1936-01-02 15:00/tick60759398，六计划1/2/6/5/4/3全false。0Post/0游戏写/0远程调用/0推进/0存档/0commit-push。最近用量观测28.7%，未声称触及约10pp门。
""")
 paths=sorted((R/'research').glob('t202_*.json'))+sorted((R/'research').glob('_t202_clip_*.txt'))+[R/'research/t202_checkpoint.md',R/'research/test_t202_boundaries.py',R/'research/t202_tests.log']
 manifest={'files':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},'checkpoint_sha256':hashlib.sha256((R/'research/t202_checkpoint.md').read_bytes()).hexdigest(),'D_sha_re_read':False};(R/'research/t202_artifact_sha256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({'checkpoint_sha256':manifest['checkpoint_sha256'],'manifest_file_count':len(manifest['files']),'tests':tests['tests_run'],'allow_post':out['allow_post'],'allow_write':out['allow_write'],'markers':out['markers'],'guard_after':after,'full_export_errors':[p['schema_error_count']for p in old],'reader_sha256':out['reader_sha256']},indent=2))
finally:x.close()
