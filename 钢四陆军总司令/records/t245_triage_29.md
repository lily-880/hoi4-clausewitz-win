# t245 剩余29项定向分流

来源：`../态势信息读取能力清单.md`；完整17内存候选/12非内存。历史边界参考Claude交接7.1/7.2、t222_checkpoint、t226_checkpoint及t244_checkpoint_BOUNDED；本块未全量读取records。

不是“所有字段均被现场阻塞”的证明；多数是证据链未完成/缺新具名入口，有些另缺自然正例。未知不冒充已证无样本。12非内存只能经配置/政策/真实回执契约验收，不能靠内存晋级。

|字段|类别|本次分流及验收依赖|
|---|---|---|
|meta.allow_write|非内存|配置许可来源/默认false及拒绝行为的契约与针对性测试；不是游戏flag。适合父级CloudAgent静态核实，不在此本地调查通用代码。|
|meta.geography_scope|非内存|配置范围类型、默认null及范围校验契约；不是heap字段。|
|policy.stance|非内存|玩家政策输入/默认值与schema枚举契约。|
|policy.instructions|非内存|用户原文的输入/传递/缺省契约，不从内存猜。|
|world.own_units.supply.isolated|内存候选|本块唯一候选：已有具名encircled consumer(E64C50/C47C40)，缺runtime生命周期写者及真隔绝正例；只取一次紧邻256字节，未产生合格写者证据，关闭这个邻域猜测，不重复C58600或46个connected样本。|
|world.visible_units.relation_to_player|内存候选|缺相对当前玩家的真实foreign-friendly对照及fresh可见owner桥；已闭合同阵营空/非战推友好不重试。|
|world.visible_units.visibility.confidence|内存候选|缺每单位具名confidence consumer；country intel/opacity/tier闭合，不重复。|
|world.plans.type|内存候选|需独立具名类型consumer及实际计划身份/对照；raw enum2与教程writer闭合。|
|world.plans.axis_province_ids|内存候选|需独立方向/箭头consumer、非空计划实际axis对照；vertex不等于axis，不查空计划。|
|world.plans.status|内存候选|需逐计划subject/status consumer及实际控制；组级alert闭合。|
|world.combats.result|内存候选|t244两次额度关闭ID桥路线，不重开。需全新typed identity witness才重新评估。|
|world.combats.started_at|内存候选|需精确当前combat对象的具名开始时间getter/存储；日期转换与duration闭合。|
|world.combats.ended_at|内存候选|需精确结束事实、对象/history身份及time字段；不借t244失败重扫。|
|world.crises.severity|内存候选|需qualified witness逐entry严重度契约及真实对照；alert ID/阈值/UI priority不算，已闭合。|
|world.wars.front_invalidated|内存候选|需具名外交war-change因果至确切当前front；invalid-key断言/occupation rebuild闭合。|
|world.shortages.equipment.deficit|内存候选|需独立国家/类型缺口consumer与真signed负余量控制；不把max派生值称原生，不重扫deficit token。|
|world.shortages.equipment.affected_plan_ids|内存候选|需装备缺口因果至真实计划ID，不以成员交集代因果，不查空计划。|
|world.shortages.manpower.needed|内存候选|需国家具名补员需求aggregate和真实控制；usage/单位missing/conveyor闭合。|
|world.shortages.manpower.deficit|内存候选|需国家独立缺口consumer和真实控制；available/单位missing求和都不足。|
|world.shortages.manpower.front_cannot_hold|内存候选|需人力导致不能维持的因果consumer和当前front；frontage_full为combat容量，闭合。|
|world.shortages.missing_divisions|内存候选|需具名front staffing缺师consumer和确切own-front；desired-force/REQ_DIVS闭合。|
|feedback.last_orders.order_seq|非内存|既有持久回执账本的序号与真实issued事件对应。|
|feedback.last_orders.type|非内存|账本命令类型及dispatch对应，不能仅取命令目录。|
|feedback.last_orders.subject_ids|非内存|同一真实回执的subject身份。|
|feedback.last_orders.target_province_ids|非内存|同一真实回执的目标身份。|
|feedback.last_orders.plan_id|非内存|同一真实回执可选计划身份与null语义。|
|feedback.last_orders.accepted|非内存|落地接受证据，不把Post返回值/超时当成功。|
|feedback.last_orders.error|非内存|原始失败原因/无错误语义，不制造失败。|
|feedback.ticks_since_issue|非内存|issue tick与当前tick的同一会话账本关系，不能用墙钟。|

## 下一项建议
优先让父级CloudAgent对`meta.allow_write`作窄配置契约核实（现有来源/默认false/禁写时fail-closed/针对性测试证据），属于12非内存之一；绝非开启WRITE/POST或将环境null当字段已验。该契约调查不能由本机memory-only研究冒充完成。若继续原生内存研究，必须先拿到一个未闭合的具名consumer入口，再取证；不再靠相邻代码/描述符猜测。当前只关闭本块邻域猜测，不全局停止持续授权，也不重开t244。
