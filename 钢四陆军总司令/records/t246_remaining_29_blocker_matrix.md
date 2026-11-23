# t246：剩余29项完整证据阻塞/责任矩阵

## 结论与边界
这不是“29项都做完”，也不是“所有项技术上不可读”。17项内存候选缺下表列明的独立语义、精确身份/因果桥或真实控制；不存在已合格的新consumer证书可直接变成晋级。12项是配置/政策/回执，不应让本机原生读内存继续空转；已有生产代码调查归父级云端，本块不越权重复。持续授权未撤销，但继续盲扫已关闭入口无法保证完成，故完成完整矩阵与实质合同核实后交回父级并行处理责任项，而非因一个路径失败停全项目。

本块没有新的用户机器或游戏进程读取，因此**不声称04:12之后游戏仍运行/暂停或PID仍为30108**；旧guard只是历史。没有复用heap，未产生自然阳性的新断言。历史无正例仅限原采样范围，不能宣称全场不存在正例。所有原生路径若以后出现新入口仍须freshguard。

### 本块实质新成果：12项非内存精确schema合同证书
从已有交接schema制品定向提取12字段，SHA256完整匹配t243生产schema pin `9a941dd3931b635591582b0d2ba3fe7ab1ceb3554a2d30af54154e61071b45ee`。这是box历史制品内容核实，非当前生产代码行为审计。
- 字段本身6必填/6可省略，12项均未声明schema default；文档默认值不等于schema自动填值。
- policy对象必填但stance/instructions可省略；不要因字段未填就要求用户无谓选政策。
- geography_scope必填，可为null/global/theater；null不自动等于global，theater需province_ids。
- plan_id/target_province_ids/error/ticks_since_issue可省略但不包含null；修正“optional即nullable”的潜在误读。
- last_orders必填但没有minItems；空数组结构允许不等于已有真实反馈账本被验收。
- order_seq/tick/ID范围、唯一性/单调性等语义并未由这个schema保证；命令enum里出现retreat不等于native能力已通。
- accepted是必填bool，不能表达未知；超时/未知如何编码必须由现有producer合同解释，不能把unknown编造成true/false。

已对这些**新合同事实**运行6个唯一离线结构检查，1轮/6调用全过。没有安装jsonschema，也没有伪造完整validator；测试不是runtime配置/ledger验证，更非真实游戏阳阴样本。0晋级，清单仍87/29，生产51/captureclosed保持。父级已发现allow_write接受值不一致，本块只登记其报告、不重复调查。

## 完整矩阵
“用户决定”列不是现在提出29个问题，也不构成新游戏动作授权。多数可先由现有授权下的源码/证据工作解决；只有确实需新自然场景或产品语义决定时才交用户，不用扩大权限替代证明。

### 1. `world.own_units.supply.isolated` — 内存候选
- 已有证据/排除：t222独立encircled consumer存在；46个历史native-connected样本不是隔绝正例；t243 loader和t245邻域均关闭。
- 精确缺口：复合补给来源隔绝的runtime生命周期写者；非仅ratio/flag/ControllerArea比较。
- 合格控制：同一独立谓词和身份下真正isolated=true与false；历史46个负例不证明当前不存在正例。
- 执行责任/关闭规则：原生研究需全新的已命名runtime入口；禁止重扫C58600/邻域/connected census。
- 用户决定：若后来提供自然已隔绝场景可重绑；不要求也不授权造包围/推进时间。
- 定位：[t222_checkpoint.md](t222_checkpoint.md)、[t243_checkpoint_STOPPED.md](t243_checkpoint_STOPPED.md)、[t245_checkpoint_BOUNDED.md](t245_checkpoint_BOUNDED.md)

### 2. `world.visible_units.relation_to_player` — 内存候选
- 已有证据/排除：方向subject/overlord有MAN→JAP正例；不是相对当前玩家关系证明。旧visible combat owner曾纠正为D04。
- 精确缺口：具名双边friend/ally或其他枚举关系，相对玩家方向，精确当前visible-owner身份桥。
- 合格控制：当前可见foreign-owner的实际关系正例/反向或敌方负例，fresh visibility；同国self、非战、空faction均不替代。
- 执行责任/关闭规则：只在有新具名双边consumer且样本可得时继续；既有null-faction/current-negative路径关闭。
- 用户决定：可能需要另一个自然可见友军场景；不自动更换玩家/宣战/造样本。
- 定位：[t240_checkpoint.md](t240_checkpoint.md)、[t241_checkpoint.md](t241_checkpoint.md)、[t242_checkpoint.md](t242_checkpoint.md)、[t245_triage_29.md](t245_triage_29.md)

### 3. `world.visible_units.visibility.confidence` — 内存候选
- 已有证据/排除：visible/spotted已窄验不代表confidence；opacity/tier/country intel路线关闭。
- 精确缺口：每个visible-unit条目具名confidence语义、单位/observer receiver与数值标度。
- 合格控制：同一当前可见身份下真实不同置信度控制；不能拿150/250阈值或alpha代替。
- 执行责任/关闭规则：需全新单位级intel consumer；不开国家intel/defines旧路径。
- 用户决定：无需放宽权限；若引擎不提供等价概念，需要用户以后决定接口语义变更，当前不降标准。
- 定位：[t224_checkpoint.md](t224_checkpoint.md)、[t235_checkpoint.md](t235_checkpoint.md)

### 4. `world.plans.type` — 内存候选
- 已有证据/排除：type2被Front/Fallback共用；CTut callback会写状态，不是type getter。
- 精确缺口：独立完整计划类型分区/注册consumer及真实COrderInstance身份，不凭类名或enum2。
- 合格控制：真实同一所有权下不同类型计划；每实例与独立具名标签桥。
- 执行责任/关闭规则：原生新注册/渲染语义入口，不调用教程writer、不轮询空计划。
- 用户决定：若缺自然计划，用户以后可提供现成场景；不得自动创建计划。
- 定位：[t239_checkpoint.md](t239_checkpoint.md)

### 5. `world.plans.axis_province_ids` — 内存候选
- 已有证据/排除：+70/递归子节点已证是vertices，不是axis；教程完成检测不输出方向。
- 精确缺口：独立方向/箭头consumer，精确有序axis语义及当前plan receiver。
- 合格控制：实际非空轴和非匹配/反向控制，不把vertex顺序换名。
- 执行责任/关闭规则：需新方向consumer证书；不重跑child-membership。
- 用户决定：自然非空进攻轴样本可后续提供；不创建/执行计划。
- 定位：[t239_checkpoint.md](t239_checkpoint.md)

### 6. `world.plans.status` — 内存候选
- 已有证据/排除：no-divs是组级警报，不是逐计划status。
- 精确缺口：每实例可执行/受阻/停滞/失效的具名consumer与schema分区。
- 合格控制：当前own-plan逐状态真控制，subject不可扩大为整组。
- 执行责任/关闭规则：需新逐计划consumer；不重扫alert group/空计划。
- 用户决定：实际阻滞状态若当前没有，需要自然样本而非执行计划制造。
- 定位：[t237_checkpoint.md](t237_checkpoint.md)、[t245_triage_29.md](t245_triage_29.md)

### 7. `world.combats.result` — 内存候选
- 已有证据/排除：历史win消费者和selector XOR事实已证；t244两动作未证identity桥。
- 精确缺口：active combat ID → retained record/pool-ref ID的确切拥有/传递关系。
- 合格控制：精确identity join后的真实胜负控制，不能用side/date/count相关性。
- 执行责任/关闭规则：t244路线关闭，除非出现全新typed identity witness；不重扫1349260邻域。
- 用户决定：自然战斗结束证据可能有用，但不授权推进时间/下令结束战斗。
- 定位：[t229_checkpoint.md](t229_checkpoint.md)、[t243_checkpoint_STOPPED.md](t243_checkpoint_STOPPED.md)、[t244_checkpoint_BOUNDED.md](t244_checkpoint_BOUNDED.md)

### 8. `world.combats.started_at` — 内存候选
- 已有证据/排除：GameDate换算、duration/int day不等于这个combat开始时间。
- 精确缺口：独立具名start-time存储/getter，精确当前combat对象/ID与clock-unit定义。
- 合格控制：真实不同起始时间的对象控制；不以当前时间减未经证明的duration。
- 执行责任/关闭规则：只接受新start consumer，日期转换路线关闭。
- 用户决定：无需先放开游戏写；若仅靠自然生命周期才能验证，需现成/自然证据。
- 定位：[t208_checkpoint.md](t208_checkpoint.md)、[t229_checkpoint.md](t229_checkpoint.md)、[t245_triage_29.md](t245_triage_29.md)

### 9. `world.combats.ended_at` — 内存候选
- 已有证据/排除：活动列表消失不能代表已验结束时间；保留历史记录仍缺active-ID桥。
- 精确缺口：具名结束事实+结束时间字段+同一combat identity。
- 合格控制：确切结束实例与仍ongoing对照；不能按日期/省份猜join。
- 执行责任/关闭规则：等待全新identity/time证据；不借此重开t244。
- 用户决定：自然结束场景可后续提供；不主动推进或操纵战斗。
- 定位：[t208_checkpoint.md](t208_checkpoint.md)、[t229_checkpoint.md](t229_checkpoint.md)、[t244_checkpoint_BOUNDED.md](t244_checkpoint_BOUNDED.md)

### 10. `world.crises.severity` — 内存候选
- 已有证据/排除：alert3/4/threshold/颜色/UI priority与static ID LUT均不是逐entry严重度。
- 精确缺口：已有3/25 witness范围内独立severity consumer及枚举映射。
- 合格控制：相同qualified subject下真实不同严重度；不扩大3/25 census。
- 执行责任/关闭规则：需新逐entry severity语义入口；先前priority/occupation配置路径关闭。
- 用户决定：若schema严重度实为产品策略，需要用户以后明确；当前不得自行映射。
- 定位：[t227_checkpoint.md](t227_checkpoint.md)、[t228_checkpoint.md](t228_checkpoint.md)、[t232_checkpoint.md](t232_checkpoint.md)、[t238_checkpoint.md](t238_checkpoint.md)

### 11. `world.wars.front_invalidated` — 内存候选
- 已有证据/排除：F6A071为invalid-key断言；occupation/共享relation rebuild不是war-change。
- 精确缺口：具名外交战争变化enqueue → exact current own-front失效的因果链。
- 合格控制：真实战争关系变化前后同front身份及有效/失效对照。
- 执行责任/关闭规则：既有empty-scope/F6A071/occupation rebuild关闭，只接受新因果入口。
- 用户决定：暂停场景不能产生新war-change样本；不宣战、不advance。
- 定位：[t233_checkpoint.md](t233_checkpoint.md)、[t234_checkpoint.md](t234_checkpoint.md)

### 12. `world.shortages.equipment.deficit` — 内存候选
- 已有证据/排除：train total83、unoccupied68是不同量；native signed remainder与派生max(0,-r)必须分开。
- 精确缺口：独立缺口consumer确认国家/装备类型的负余额语义，不能只取token。
- 合格控制：同类stock/request语义下真正native负余量与非负对照。
- 执行责任/关闭规则：既有demand/deficit-token路线关闭；需要具名negative-balance consumer。
- 用户决定：若要改成派生指标须另行接口决定；本轮不更改定义或制造缺装。
- 定位：[t221_checkpoint.md](t221_checkpoint.md)

### 13. `world.shortages.equipment.affected_plan_ids` — 内存候选
- 已有证据/排除：缺装师ID/部署警报不等于作战计划因果。
- 精确缺口：官方装备需求到确切COrderInstance plan ID的影响关系。
- 合格控制：真实受影响计划与不受影响计划，证实因果而非成员交集。
- 执行责任/关闭规则：需新计划owned shortage consumer；不重采空计划。
- 用户决定：若当前无真实受影响计划，需自然样本；不能创建计划或耗装备。
- 定位：[t223_checkpoint.md](t223_checkpoint.md)

### 14. `world.shortages.manpower.needed` — 内存候选
- 已有证据/排除：MANPOWER_USAGE是分类占用；单师补员/CONVEYOR_MANPOWER_NEED都非国家补充总需。
- 精确缺口：国家级具名reinforcement aggregate consumer及范围/单位。
- 合格控制：真实国家需补为正与零/其他量对照，不能拿8师missing0推出全国0。
- 执行责任/关闭规则：旧usage/unit/conveyor路线关闭；需新国家aggregate入口。
- 用户决定：正例缺失时需自然场景；不损伤单位或动员造样本。
- 定位：[t226_checkpoint.md](t226_checkpoint.md)

### 15. `world.shortages.manpower.deficit` — 内存候选
- 已有证据/排除：available中央池+州池已证，单位missing已证，但都不等于国家deficit。
- 精确缺口：独立国家缺口consumer，区分required、available、delivery和deficit。
- 合格控制：真实国家缺口正负/零控制及完整范围，不合计少数单位冒充全国。
- 执行责任/关闭规则：需要新国家deficit入口；复用已证available与单位控制只作非替代反例。
- 用户决定：若用户实际想要derived缺口须单独界定，不默改库存定义。
- 定位：[t207_checkpoint.md](t207_checkpoint.md)、[t226_checkpoint.md](t226_checkpoint.md)、[t245_triage_29.md](t245_triage_29.md)

### 16. `world.shortages.manpower.front_cannot_hold` — 内存候选
- 已有证据/排除：frontage_full是combat有效宽度/容量，不是人力因果。
- 精确缺口：人力不足→具体current-front不能维持的具名因果consumer。
- 合格控制：真受人力约束front与非该原因对照，不能以损失/兵少/宽度代替。
- 执行责任/关闭规则：frontage capacity路径关闭；需新因果入口。
- 用户决定：需要自然人力约束样本，绝不通过战损/撤兵制造。
- 定位：[t236_checkpoint_BOX_PENDING_C.md](t236_checkpoint_BOX_PENDING_C.md)、[t237_checkpoint.md](t237_checkpoint.md)

### 17. `world.shortages.missing_divisions` — 内存候选
- 已有证据/排除：desired force/required-minus-assigned/garrison REQ_DIVS不能等同前线缺师。
- 精确缺口：具名front-staffing consumer、exact own-front membership和缺师定义。
- 合格控制：真实不能维持的front缺师正例及足额负例。
- 执行责任/关闭规则：已闭合desired-force/REQ_DIVS路径不重扫；需要新staffing入口。
- 用户决定：若仅有空front/非战线场景，用户以后提供自然样本；不布防造样本。
- 定位：[t230_checkpoint.md](t230_checkpoint.md)

### 18. `meta.allow_write` — 非内存
- 已有证据/排除：schema必填boolean且没有default；父级云端报告解析接受值不一致，未在本块重查。
- 精确缺口：config许可、Backend handle/write许可和Input字段的同一解释及默认/拒绝契约。
- 合格控制：完全离线的许可输入表/编码boolean一致性；不能实际写游戏测试，不以env unset晋级。
- 执行责任/关闭规则：父级云端已接手；本块不重复生产代码调查。
- 用户决定：无需放开WRITE/POST。若契约需修改由父级明确处理。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)、父级t215u云端审计报告（未独立复跑）

### 19. `meta.geography_scope` — 非内存
- 已有证据/排除：schema必填，null/global/theater三形；theater必带province_ids；无schema默认。
- 精确缺口：实际配置来源、序列化、作用域包含规则与越界fail-closed。
- 合格控制：离线null/global/theater有效/无效输入、未知kind、缺province_ids、越界对象拒绝；null不能自动解释为global。
- 执行责任/关闭规则：父级云端只读核实生产配置/consumer；不由本机例外调查。
- 用户决定：只有要选实际非默认指挥范围时才需用户决定；不擅自扩大范围。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

### 20. `policy.stance` — 非内存
- 已有证据/排除：policy对象root-required，但stance本身可省略；五个命名枚举；无schema默认。
- 精确缺口：玩家政策来源、缺省规则、enum传递与consumer解释。
- 合格控制：离线省略/五种合法值/非法值；schema通过不能证明已使用政策。
- 执行责任/关闭规则：父级云端核实既有policy来源；本块只给合同。
- 用户决定：仅真实要采用具体作战方针时需用户选择；不自行选annihilate等。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

### 21. `policy.instructions` — 非内存
- 已有证据/排除：可省略string；不是把用户给机器人的工具安全指令自动塞入作战政策。
- 精确缺口：原文来源、传递/转义/缺省及身份绑定。
- 合格控制：离线空串/省略/中文多行原文roundtrip、非string拒绝。
- 执行责任/关闭规则：父级云端核实policy输入接口；不由内存反推。
- 用户决定：只有需要自定义作战原文时请用户提供；不是现在追问的必要条件。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

### 22. `feedback.last_orders.order_seq` — 非内存
- 已有证据/排除：每条receipt必填integer；schema没有minimum/monotonic/唯一性保证。
- 精确缺口：可追溯issued ledger、唯一序号、会话/重复回执规则。
- 合格控制：真实既有账本记录的顺序/重复/跨会话控制；若无现成账本不得制造命令。
- 执行责任/关闭规则：父级云端先确认现有ledger位置和生产consumer，优先离线旧真实回执。
- 用户决定：不需要新写许可；没有真实回执时明确缺证而非编造seq。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)、[t198_checkpoint.md](t198_checkpoint.md)

### 23. `feedback.last_orders.type` — 非内存
- 已有证据/排除：必填命名enum union，含retreat/unknown等不代表已有对应Post ABI。
- 精确缺口：同一issued序号的dispatch命令名与receipt类型映射。
- 合格控制：现成真实回执与命令类型一致/不一致对照；catalog枚举不足。
- 执行责任/关闭规则：父级云端核实ledger类型绑定，不调用native工厂。
- 用户决定：无需开放任何命令；Retreat仍不能因schema枚举升格。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)、[t244_checkpoint_BOUNDED.md](t244_checkpoint_BOUNDED.md)

### 24. `feedback.last_orders.subject_ids` — 非内存
- 已有证据/排除：必填integer数组；schema无minItems/uniqueItems/ID范围。
- 精确缺口：同一issued事件中subject身份与实际目标集合的追踪。
- 合格控制：真实receipt subject、空/重复/过期身份的离线处理；只schema数组通过不够。
- 执行责任/关闭规则：父级云端核实ledger subject来源与会话命名空间。
- 用户决定：没有可追踪旧receipt时不能补猜IDs。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

### 25. `feedback.last_orders.target_province_ids` — 非内存
- 已有证据/排除：可省略integer数组，不包含null；schema无成员范围/去重保证。
- 精确缺口：同一issued事件的目标省份来源及无目标命令的省略规则。
- 合格控制：真实targeted/non-targeted receipt，省略与null/空数组区别。
- 执行责任/关闭规则：父级云端核实命令payload→ledger传播；不发命令采样。
- 用户决定：无需新游戏操作许可；必要时提供现成回执。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

### 26. `feedback.last_orders.plan_id` — 非内存
- 已有证据/排除：可省略integer，但null并非合法声明类型；可省略不等于nullable。
- 精确缺口：同一issued事件plan身份与无关联计划时的省略规则。
- 合格控制：真实关联/不关联计划旧回执，拒绝猜填0或null。
- 执行责任/关闭规则：父级云端检查ledger计划绑定/生产编码；不创建计划。
- 用户决定：若没有真实计划回执，保持未验证，不编造负例。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

### 27. `feedback.last_orders.accepted` — 非内存
- 已有证据/排除：每条receipt必填boolean；不能表示null/unknown；Post返回1和WAIT_TIMEOUT258都不独立证明落地。
- 精确缺口：独立consume/执行/拒绝事实与issued事件的绑定；未知结果如何不误报。
- 合格控制：既有真实落地/拒绝回执，超时/未知控制；不以返回值强塞true/false。
- 执行责任/关闭规则：父级云端优先核实unknown处理：省略receipt/外部错误等产品契约，不在此自行选。
- 用户决定：若缺现成真实结果证据，不能为了验收再Post；需要以后另授权且本轮不请求放开。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)、[t198_checkpoint.md](t198_checkpoint.md)、[../README.md](../README.md)

### 28. `feedback.last_orders.error` — 非内存
- 已有证据/排除：可省略string，不包含null；成功无错误与未知失败要分开。
- 精确缺口：原始错误来源/类别/序号绑定及成功/无错误省略语义。
- 合格控制：既有真实失败及成功receipt，不制造权限/游戏失败当正例。
- 执行责任/关闭规则：父级云端核实error来源和编码，不把未知落地填空串充成功。
- 用户决定：无需新写入；缺真实失败记录就标缺证。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

### 29. `feedback.ticks_since_issue` — 非内存
- 已有证据/排除：feedback级可省略integer，不包含null，也无minimum；不是每条last_order内字段。
- 精确缺口：issue tick来源、tick单位/会话、多个last_orders时取哪条、重启/回绕策略。
- 合格控制：同一会话旧issued_tick与已证current_tick的精确差；负差/跨会话/多条/暂停控制。
- 执行责任/关闭规则：父级云端核实ledger clock contract；禁止将wallclock或不同会话tick相减。
- 用户决定：没有同会话issue锚点则保持省略/未验证；不发命令造锚点。
- 定位：[t246_nonmemory_contracts.json](t246_nonmemory_contracts.json)

## 父级云端的明确问题（非本机生产代码调查）
1. allow_write已有云端审计负责人继续统一契约核实，本块不重复；默认false、bool编码与许可解析的分歧不得通过放宽后端或开门掩盖。
2. geography_scope：生产入口在哪里接收/序列化？null究竟是unknown还是无范围？theater membership何处fail-closed？仅做静态/离线，不运行旧doctor/status。
3. policy：stance/instructions的省略/默认/用户来源在哪里定义？是否有实际producer？不得替用户选方针或把机器人执行权限当游戏政策。
4. feedback：现有ledger/receipt生产者究竟在哪里？八项能否用现成真实回执追溯到同一issued/session/subject？不存在则明确属于待实现，不能在严格只读下制造命令。尤其accepted二值如何处理未知、可选字段省略而非null、反馈级ticks_since_issue对应哪条issue。
这些问题不授权生产改动；需要实现或契约变更时由父级依用户范围另行安排。当前不能因为配置默认/Schema结构通过就晋级12项。

## 持续工作止损规则
原生研究只有获得一个真正新具名consumer/identity/因果入口，才做窄验证并取真实控制；每路径最多两次无新增证据关闭，非“每字段必须盲读两遍”。t244 combat-ID与t245 isolated邻域保持关闭。不存在用换字段不断产空记录的后续计划。持续授权不等于允许无限扫、造样本、写游戏、读存档或把输入合同改成方便完成的定义。

当前成果可供父级推进的不是29个已验证标记，而是12项精确合同、29项完整缺证/责任清单，以及可追溯的关闭入口。若用户坚持当前暂停现场且不提供自然样本，真实控制依赖的项不能保证全部完成；这是真实证据条件，不是配额或单路径失败停工。
