# t247：剩余29项精确执行阻塞矩阵（合并云端t246结论）

## 当前成果与工作边界
用户t214u/t215u持续验证和成果同步授权仍有效。这里不是29项已完成，也不是单路径失败停整个工作：已经汇总全部29项的独立证据/样本/实现依赖。没有可凭现有已关闭入口直接晋级的合格新consumer；不能靠换字段盲读、放宽语义或制造样本保证“做完”。

17项内存候选与12项非内存严格分开。内存表里的“缺证”不等于证明引擎没有该字段或全场没有阳性；历史样本缺失不冒充当前现场普查。后续只在出现未闭合具名入口/自然控制时继续该路径，每路径最多两次无证据关闭，绝不重开t244 combat-ID、t245隔绝邻域、空faction/country-confidence/空计划/日期转换。

本阶段后半只做box文档/离线合同及指定文件同步，**没有04:12以后的游戏进程读取**，所以没有新的PID/base/player/pause/tick现场断言。旧PID30108与heap只属历史。任何以后live读取仍先freshguard，必须pause1/speed0且0x410只读；所有gamewrites/Post/nativegamecalls/saveaccess/time/UI/pause-speed更改保持0。

清单保持87/29（17memory+12nonmemory），14表116字段3列；SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3。生产51、complete_input=false/captureclosed不变。

## A. 17项内存候选：精确尚缺证书
|字段|缺的独立语义/精确身份或因果|必须具备的真实控制|现有入口状态与定位|
|---|---|---|---|
|`world.own_units.supply.isolated`|复合补给来源隔绝的runtime生命周期写者；非仅ratio/flag/ControllerArea比较。|同一独立谓词和身份下真正isolated=true与false；历史46个负例不证明当前不存在正例。|原生研究需全新的已命名runtime入口；禁止重扫C58600/邻域/connected census。 [t222_checkpoint](t222_checkpoint.md)、[t243_checkpoint_STOPPED](t243_checkpoint_STOPPED.md)|
|`world.visible_units.relation_to_player`|具名双边friend/ally或其他枚举关系，相对玩家方向，精确当前visible-owner身份桥。|当前可见foreign-owner的实际关系正例/反向或敌方负例，fresh visibility；同国self、非战、空faction均不替代。|只在有新具名双边consumer且样本可得时继续；既有null-faction/current-negative路径关闭。 [t240_checkpoint](t240_checkpoint.md)、[t241_checkpoint](t241_checkpoint.md)|
|`world.visible_units.visibility.confidence`|每个visible-unit条目具名confidence语义、单位/observer receiver与数值标度。|同一当前可见身份下真实不同置信度控制；不能拿150/250阈值或alpha代替。|需全新单位级intel consumer；不开国家intel/defines旧路径。 [t224_checkpoint](t224_checkpoint.md)、[t235_checkpoint](t235_checkpoint.md)|
|`world.plans.type`|独立完整计划类型分区/注册consumer及真实COrderInstance身份，不凭类名或enum2。|真实同一所有权下不同类型计划；每实例与独立具名标签桥。|原生新注册/渲染语义入口，不调用教程writer、不轮询空计划。 [t239_checkpoint](t239_checkpoint.md)|
|`world.plans.axis_province_ids`|独立方向/箭头consumer，精确有序axis语义及当前plan receiver。|实际非空轴和非匹配/反向控制，不把vertex顺序换名。|需新方向consumer证书；不重跑child-membership。 [t239_checkpoint](t239_checkpoint.md)|
|`world.plans.status`|每实例可执行/受阻/停滞/失效的具名consumer与schema分区。|当前own-plan逐状态真控制，subject不可扩大为整组。|需新逐计划consumer；不重扫alert group/空计划。 [t237_checkpoint](t237_checkpoint.md)、[t245_triage_29](t245_triage_29.md)|
|`world.combats.result`|active combat ID → retained record/pool-ref ID的确切拥有/传递关系。|精确identity join后的真实胜负控制，不能用side/date/count相关性。|t244路线关闭，除非出现全新typed identity witness；不重扫1349260邻域。 [t229_checkpoint](t229_checkpoint.md)、[t243_checkpoint_STOPPED](t243_checkpoint_STOPPED.md)|
|`world.combats.started_at`|独立具名start-time存储/getter，精确当前combat对象/ID与clock-unit定义。|真实不同起始时间的对象控制；不以当前时间减未经证明的duration。|只接受新start consumer，日期转换路线关闭。 [t208_checkpoint](t208_checkpoint.md)、[t229_checkpoint](t229_checkpoint.md)|
|`world.combats.ended_at`|具名结束事实+结束时间字段+同一combat identity。|确切结束实例与仍ongoing对照；不能按日期/省份猜join。|等待全新identity/time证据；不借此重开t244。 [t208_checkpoint](t208_checkpoint.md)、[t229_checkpoint](t229_checkpoint.md)|
|`world.crises.severity`|已有3/25 witness范围内独立severity consumer及枚举映射。|相同qualified subject下真实不同严重度；不扩大3/25 census。|需新逐entry severity语义入口；先前priority/occupation配置路径关闭。 [t227_checkpoint](t227_checkpoint.md)、[t228_checkpoint](t228_checkpoint.md)|
|`world.wars.front_invalidated`|具名外交战争变化enqueue → exact current own-front失效的因果链。|真实战争关系变化前后同front身份及有效/失效对照。|既有empty-scope/F6A071/occupation rebuild关闭，只接受新因果入口。 [t233_checkpoint](t233_checkpoint.md)、[t234_checkpoint](t234_checkpoint.md)|
|`world.shortages.equipment.deficit`|独立缺口consumer确认国家/装备类型的负余额语义，不能只取token。|同类stock/request语义下真正native负余量与非负对照。|既有demand/deficit-token路线关闭；需要具名negative-balance consumer。 [t221_checkpoint](t221_checkpoint.md)|
|`world.shortages.equipment.affected_plan_ids`|官方装备需求到确切COrderInstance plan ID的影响关系。|真实受影响计划与不受影响计划，证实因果而非成员交集。|需新计划owned shortage consumer；不重采空计划。 [t223_checkpoint](t223_checkpoint.md)|
|`world.shortages.manpower.needed`|国家级具名reinforcement aggregate consumer及范围/单位。|真实国家需补为正与零/其他量对照，不能拿8师missing0推出全国0。|旧usage/unit/conveyor路线关闭；需新国家aggregate入口。 [t226_checkpoint](t226_checkpoint.md)|
|`world.shortages.manpower.deficit`|独立国家缺口consumer，区分required、available、delivery和deficit。|真实国家缺口正负/零控制及完整范围，不合计少数单位冒充全国。|需要新国家deficit入口；复用已证available与单位控制只作非替代反例。 [t207_checkpoint](t207_checkpoint.md)、[t226_checkpoint](t226_checkpoint.md)|
|`world.shortages.manpower.front_cannot_hold`|人力不足→具体current-front不能维持的具名因果consumer。|真受人力约束front与非该原因对照，不能以损失/兵少/宽度代替。|frontage capacity路径关闭；需新因果入口。 [t236_checkpoint_BOX_PENDING_C](t236_checkpoint_BOX_PENDING_C.md)、[t237_checkpoint](t237_checkpoint.md)|
|`world.shortages.missing_divisions`|具名front-staffing consumer、exact own-front membership和缺师定义。|真实不能维持的front缺师正例及足额负例。|已闭合desired-force/REQ_DIVS路径不重扫；需要新staffing入口。 [t230_checkpoint](t230_checkpoint.md)|

### 内存类真正需要用户决定的情形
- 若后续独立语义已齐但缺自然隔绝/友军可见/人力缺口/计划受阻/战斗结束/war-change正例，需要用户以后提供已有自然场景或明确允许某种取证条件；**本轮不要求也不授权任何推进时间、下令、换玩家、改存档或制造样本**。
- 缺具名consumer/精确ID或因果链本身，首先是研究证据缺口，不应一律推给用户；但在已关闭路径上再扫邻域/日期/计数不算工作进展。若实际想把字段改成派生量或产品策略，必须另定接口合同，不能为清单晋级自行重定义。

## B. 12项非内存：云端已审计的实现阻塞
云端固定提交`88f995ae13d04902f643c52efe8fd51f4b1d15ba`的[主报告](t246_nonmemory_12.md)、[逐项证据](t246_nonmemory_12.json)、[测试源](test_t246_nonmemory_contract.py)、[manifest](t246_manifest.json)已经按父级给定size/SHA原字节同步。下列实现结论来自云端审计，不是本机重复调查或重新运行其测试。报告指出生产capture对这12字段均未赋值。

|字段|具体实现/验收阻塞|所需用户/父级动作（不等于游戏写授权）|
|---|---|---|
|`meta.allow_write`|config去空白后接受1/true/TRUE/yes；Backend句柄/write仅精确1。报告与有效许可不一致，生产不输出字段。|父级处理契约；仅收窄报告至精确1的最小方案未实施，不得扩大Backend许可。即修复也须另验输出，不自动晋级。|
|`meta.geography_scope`|无读取函数/生产缺键；不是实际JSON null。schema必填且允许null/global/theater。|用户明确范围选择；theater需province_ids。父级实现/验输入和越界拒绝；不能自动把null当global。|
|`policy.stance`|无存储/消费者，无具体默认；schema五枚举但字段可省略。|要完成该字段需用户选择preserve_force/hold_line/annihilate/economize_manpower/custom之一，并有输入通道；不得擅选。|
|`policy.instructions`|无用户原文通道；省略与空串语义未定义。|需要用户实际作战方针原文及父级输入通道；不把给机器人“继续/只读”的工具权限指令伪装成作战政策。|
|`feedback.last_orders.order_seq`|无真实receipt账本/issued序号；空last_orders只结构合法。|先有可追踪真实旧回执/生产账本；不合成seq、不发命令造账本。|
|`feedback.last_orders.type`|无同一真实回执来源；目录/enum不是实际issued类型。|绑定同一序号/会话的真实命令类型；Retreat在enum中不代表native ABI可用。|
|`feedback.last_orders.subject_ids`|无同一真实receipt的subject来源。|绑定真实issued对象，不拿当前单位号冒充历史回执。|
|`feedback.last_orders.target_province_ids`|无同一真实receipt目标；可选但不是nullable。|需要真实目标或明确省略规则，不猜填目标/空数组/null。|
|`feedback.last_orders.plan_id`|无真实receipt-plan绑定；可选integer但不接受null。|需要真实关联计划或明确省略；不创建计划制造证据、不改schema加null。|
|`feedback.last_orders.accepted`|无实际落地账本；Post acknowledgement/WAIT_TIMEOUT不是执行证明。必填bool不能表达unknown。|父级明确unknown如何处理，取得现成真实落地/拒绝证据；不填假true/false、不再次Post验证。|
|`feedback.last_orders.error`|无真实失败账本，无“省略/空串=无错误”的合同。|需要原始错误来源及成功省略规则，不制造失败字符串或无错哨兵。|
|`feedback.ticks_since_issue`|无同一会话issue tick/当前tick链；pause receipt模块无节拍运算。|需要同会话issue锚点、单位/回绕/多条订单规则；不能墙钟替代、跨会话相减或发命令造锚点。|

### 非内存合同的结构注意事项（不是晋级）
已有精确历史schema制品SHA与t243生产pin一致；本机先前另做过6个唯一标准库结构检查，1轮6调用全过，发生在本次云端4文件同步指令之前。两组不同来源的6项检查不能合称12个字段完成，也没有在同步后重跑云端已通过的6测试。

这12字段本身6必填/6可省略，均无schema default；policy对象root-required但其两个成员可省略。可选不等于nullable；last_orders无minItems不代表已验“没有命令”；schema未保证序号/ID/tick的范围、单调性/唯一性。更详细云端实现审计已经提交，不重复发布本机那套5份schema-only制品，保留在C/box作本地审计即可。

## C. 文件同步的真实边界
截至2026-11-22 04:22:24 EST，固定云端4文件已在box/C权威逐文件size/SHA匹配；Windows checkout缺失的t244+t245七文件及云端四文件共11个文档路径以CreateNew增补并核SHA，异字节不覆盖。无git reset/checkout/commit/push，未触碰原有其他dirty文件；**不是把本地分支/HEAD同步到云端提交**，也不是main已合并。

权威目录`C:\Users\Lenovo\Documents\钢四陆军总司令\records`；checkout仅文档镜像`C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win\钢四陆军总司令\records`；box镜像`/workspace/hoi4-docs-latest/records`。详见[t247同步回执](t247_cloud_sync_receipt.json)。退休D文档目录未访问，exe正常只读许可没有扩大为D盘普查。

本次只追加这份完整矩阵和同步回执供父级云端提交；不再打包已上PR1的11文件，不提交重复schema-only材料。0新字段晋级、0新增live采样、0新增测试。后续有实质新入口/自然样本或父级完成输入/账本合同后可resume；没有声称整个29项已做完。
