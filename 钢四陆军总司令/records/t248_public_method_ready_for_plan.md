# t248 公开方法研究：具名动态变量的scope→原生receiver交叉定位

## 本轮确切结果
找到一个此前关闭邻域之外、可操作但**尚未实机验证**的定位候选：公开生成文档中的 `unit_ratio_ready_for_plan`。它在明确的 `unit_leader` scope下描述为 **“ratio of units that are ready for plan”**，可作为剩余 `world.plans.status` 的独立readiness consumer入口线索。不是schema status原生枚举，也不是逐计划语义已证；若最后只是leader/group聚合，仍不能晋级该字段。

方法区别于此前盲读相邻代码、教程callback或组级no-divs警报：先用游戏生成的**动态变量名称+显式scope合同**筛选精确计算回调，再独立绑定当前country/leader接收者，最后检验是否有确切COrderInstance参数/成员关系。只看名称、描述符邻词或类名仍不够。

## 可追溯公开来源
1. https://hoi4doc.dev/type/documentation — 自述收录游戏documentation目录中的11类文档，含Dynamic Variables与Triggers。
2. https://hoi4doc.dev/item/documentation-dynamic_variables_documentation — 明确：dynamic variables为read-only，使用时由引擎计算返回。其`Dynamic variables for scope unit_leader`末尾含上述精确名称和描述。该页scope/句子本轮实际读到，不是搜索摘要猜测。
3. https://hoi4doc.dev/item/documentation-triggers_documentation — 逐trigger列Supported Scopes/Targets，提供独立scope核对机制。这里只证明公开方法，不把scope等同当前对象身份。
4. https://hoi4doc.dev/type/dynamic_variable — 最后一页读取没有定位到该条目canonical链接，也没有可核实的1.19版本标识。不得补造链接/具体版本。

HOI4DOC是第三方托管的游戏文档索引，不是Windows1.19.5二进制符号保证。本轮没有找到可核实的1.19.x专用PDB/符号包、Grok Bot成功复现案例或“许多用户已在此build实证”的证据。普通modding公开文档属于允许使用的资料路径，但**文档公开/read-only变量并不授权在游戏调用它**。

## 下一次有收益的窄验证（本轮未执行）
1. 先只读确认实际1.19.5安装**已有**文档或脚本资料中是否含同名变量及unit_leader scope；若不存在，记录版本/资料缺口停止，不能套用外部版本地址。不要执行`docs/trigger_docs/eval_trigger`等控制台命令来生成或评估资料，不重启、不装mod、不写游戏文件/日志。
2. 若同版本名称确实存在，在新的最小freshguard通过后，只定位该**精确注册名**对应的native compute callback和scope适配器。仅静态读代码，不调用注册器/formatter/计算回调，不扫全库或整段text。
3. 独立验证回调receiver是country归属明确的真实leader/其组，而不是国家intel、教程对象或邻近descriptor。检查是否真的使用逐计划身份；如果仅leader/group比率或未绑定plan的聚合，立即关闭作为plans.status晋级路径，不重复空计划采样。
4. 仅在发现确切逐计划bridge后，才需要真实当前own-plan的readiness正反例，并独立证明ready与schema状态的关系。比率不可自行映射成executable/blocked/stalled/invalidated。没有自然样本不制造计划/时间推进；最多两次无新证据关闭该路径。

此时无需向用户索要政策选择或造新场景。最先要回答的一个问题是：**同版本是否存在这个具名变量，并且它的计算对象能否精确落到单个当前计划，而非整位leader的聚合？** 本轮不预设答案。

## 预算与不采用的路线
完整读取unblock-research技能后，先查既有能力/记忆，再做公开web与X。保守把RecallMemory也计入：共3次search=1memory+1WebSearch+1公开X搜索，未分页。X查询同时包含Grok Bot/@bot及HOI4/Clausewitz/reverse-engineering条件，返回3条无关内容，没有可采纳技术方法，未当作成功案例。

WebSearch查询：`HOI4 Windows 1.19 reverse engineering read only trigger localization generated documentation 2026`。
X查询：`((hoi4 OR clausewitz) ("reverse engineering" OR localization OR triggers)) OR (("Grok Bot" OR "@bot") (hoi4 OR clausewitz OR "memory reading")) -is:retweet`。

共5次公开page读取：documentation索引WebFetch、同页普通HTML取链接、dynamic变量文档、trigger文档、dynamic_variable索引普通HTML。后续只分析本地缓存，不再搜索/读网页；没用内部API、API key、登录cookie或未知exe。搜索结果提到的console生成文档/执行trigger被明确排除，不运行。

## 安全与结论级别
本轮game/process/exe/save读取0、写入/Post/nativegamecalls/timeadvance/pause-speed/UIchanges0；没有测试、字段晋级、清单/生产修改或新现场PID断言。仍87/29、生产51、captureclosed。这里只保存一个有来源、明确限界的**新方法候选**，不保存成“已成功验证”的技能，也不谎称找到了合格原生消费者。若后续同版本/receiver证据失败，就如实关闭，不重开t244 combat-ID或t245孤立邻域。
