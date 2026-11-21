# t201 checkpoint（持续严格只读）

已加载code-changes，按本机活体依赖例外。开段重新发现PID、映像base、GS/player/idler并核对exe SHA，不沿用堆指针。官方暂停、speed0、全部已读计划executing=false，闸门关闭。0Post/0游戏写入/0远程调用，无存档/commit/push。
块1新链：CSupplyConsumer vtable构造引用、具体UI supply标签调用者、FC9880直接调用者、Combat两计数更新及基构造的直接调用者已新建xref证据。后续沿这些根函数拆解，非重复短访问器扫描。

## 块2：已找到真实师级补给UI与计划UI所有者（未升格）
ARMY_UNIT_SUPPLY_DESC_BAD/OK位于1744D30，其分支明确调用CArmy主vt+158=CE4F10，数值由CE4CD0给出，buffer值由vt+180=CE4C20给出。CE4CD0完整叶函数：当Army+600>0时，以max(Army+40, Army+610/全局buffer天数)裁剪至[0,100000]；CE4F10对相同组合量与全局阈值比较，但+2F8特殊态直接不判缺补给。与consumer+30=Army+40的继承定位吻合；不能把单一字段默认1当成完整满足率。已避免先前64字节叶函数截断，完整证据见t201_semantic_bridges.json。
FC9880的两个调用者E733AB/E7645D通过idler虚槽+C8取得对象；新只读槽确认E33D70返回idler+A48；E4ABF0先分配0x328字节、调用FC31C0再存入+A48。继续沿该真实UI对象的+224写点，而非在COrderInstance+224强套枚举。
Combat1489550确实写+E8=GS小时值减固定epoch、+E0=2后尾调1347FD0，但现有CLandCombat原始头+E0为指针，不能当通用陆战phase/start；正在利用方法指针归属vtable辨别派生类。历史原始头无需重复活体探测。
库存仍72/44、14表116字段3列，SHA未改；本段到此用量读数26.6%，不作为开段基线。

## 块3：真实非默认补给正反样本与完整capture
新只读读取21师官方UI公式各输入；buffer参数72、阈值99000。9师不足（1831-1835/1840/1841/1847/1848），12师正常。实际source比例约0.61279-0.61285或0.91240；保留储备后有效比例0.89105-0.89107或0.97536，不能把Army+40直当最终ratio。已添加有边界/溢出拒绝和依赖复读的unit_supply并接入完整capture。两个端到端导出observation完全相同，21师均输出ratio/in_supply，isolated仍省略。官方暂停与游戏日期/全部计划执行状态读前后完全相同。
两项已有新活体正反证据，本地记录为证实待清单同步。但D盘目标的Read和专用CopyToBox均被allowed local-exec root拒绝，未改用Shell绕过，未写D盘，也不能声称新SHA读回。最后确认清单仍72/44、SHA4219d8b0fa9c800fdb34ce3f2b12256c0a28490b21cf12da411f8dbe73aba91a；两项状态同步后应为74/42，非已写入事实。
Combat静态vtable归属已确证1489550是CLandBorderWarCombat槽78，而普通CLandCombat槽78=1347FD0、槽80=1348D30。边境战+E8开始时间不能移植普通陆战。
离线保存t198原始源码及SHA；修正提前清除unpaused风险，只有官方pause1才能清除；异常路径不重用已Post对象，不再含自动重试执行器。历史脚本首行硬阻止执行。只编译/AST与纯函数回归，未执行历史脚本，未活体复现。并未找全预制暂停底层失败根因。

## 块4：计划UI桥接、50项回归通过与隔离新入口
FD2DC0中FD4682调用12DF090返回r15实例；FD4742对其+298 fallback分支为真时UI+224=1；否则FD4760按实例+30==1选择UI0，不等于1选UI2（r14已清零）；另+119特殊标志走UI4。FC9880已知UI0/1/2分别defensive/fallback/offensive。当前type2+fallback0不能称frontline；当前fallback1在schema无枚举，不能强塞frontline。继续校验12DF090→C402A0实例身份及特殊+119边界，仍不升格计划type。
剩余新链：CHANGE_TEMPLATE_DISABLED_ENCIRCLED位于1739900的原因码4分支；HQ_WITHDRAWAL/DEPLOYMENT_BLOCKED_ENCIRCLED的真实判断调用分别C47C40/C47880，已开始拆函数，而非把out-of-supply直接等同isolated。
50项离线回归全部通过（新增16项；第一次仅UTF-8导出被Windows默认GBK解码，测试明确指定UTF-8后通过；无需重采样）。完整capture依旧50项required缺失，complete_input=false，未冒称全合同完成。
宽GS+268/虚槽扫描含大量其他对象+268甚至call/stack偏移碰撞，不能作为调度者证据；已改为显式GS全局来源的寄存器传播筛选，结果只作后续候选。

## 块5：普通陆战计数已接上官方小时调度，计划实例桥已闭合
不是在GS+268找直接循环：它是GS+260管理器的+8数组。已有证实hourly根1F5230在1F604B取this+260，1F6052调用C0C660；C0C660从manager+8/+14迭代战斗，C0C941调用vslot78（CLandCombat=1347FD0，1348025增duration+44）；C0CADD调用vslot80（1348D30，1348DA5增+40）。因此两计数的更新调度是小时，不是因命名day而推定现实日。当前23/23与样本吻合；仍缺创建与同小时调度先后关系及普通战斗显式起讫时间，不能直接把now-duration当精确started_at升格。边境战专属+E8仍排除。证据t201_combat_hourly_manager.json。
已实现正确合并PE UNW_FLAG_CHAININFO相邻片段，1347FD0不再只取6条序言，完整到13480D0尾调用147E600。
C402A0确实遍历COrdersGroup三列表+98/+B0/+C8，调用10AF270按COrderInstance+244 ID查找，并递归+1F8/+2D0子列表；由此12DF090→C402A0→10AF270→FD4742/FD4760→UI+224→FC9880的实例桥闭合。fallback=true明确UI1，非fallback且rawtype2明确UI2(offensive)；不可统一称frontline。最终只读补充+119及两个子列表，详见t201_final_status.json；无schema支持的fallback不输出伪枚举。
隔离支线边界细化：1739900是原因码formatter非师级getter；C47C40/C47880来自HQ阻塞tooltip上下文，依赖+19B/+199及+68/+50对象再调E64C50，尚未绑定其this为CArmy，不能将这些偏移套在师上。原生小写字符串只有encircled_divisions等聚合统计，不能等同supply.isolated。
## 块6：落盘与接续（不是宣布整项结束）
新确证2项供给字段，已接入reader与完整capture；50项回归通过。全capture含21师/12省/2集团军/1集团军群/4计划/2战斗，9不足/12正常，完整合同仍50个required缺失、complete_input=false。两次observation完全一致，不把带采集时间的整JSON哈希差异当观察不稳定。
D盘同步受根目录权限阻断，专用Read/CopyToBox均拒绝；未绕过、未更新，不能声称新D盘SHA。精确待改两行状态在t201_promotions_pending_inventory.json。原清单最后确认72/44；本地新证据计入后74/42（剩余内存30项+非内存12项），二者不可混称。本地t201_candidate_triage.json已保留二者差异。
接续优先：A. 受支持的UI2/offensive映射可做局部reader输出，但fallback在既定schema无枚举，保持不造字段值；追+119特殊分支、child+1F8/+2D0语义与axis消费者。B. C0C660→1347FD0/1348D30已证明小时调度，下一步沿创建函数133A150/构造147C240及147E600统计记录确认精确起止与真manpower casualties，不用HP代替。C. isolated继续追师级命令CanChangeTemplate原因码4的生产者，而非HQ UI对象。D. 暂停仅离线：原始payload/clone/Execute链仍缺失败对象字节，不复现、不自动Post。
最后一次新只读状态见t201_final_status.json：PID12948，官方暂停，速度槽0，1936-01-02 15:00，tick60759398；所有已观察计划executing=false，闸门关闭，0Post/0游戏写入/0远程调用。没有存档访问或commit/push。本机只读研究仍有新线索可供父代理继续，不以静态快照为终止理由。

## 块7：最终新样本揭示递归遗漏，已修reader并再次完整端到端验证
块6后的新只读结构确认发现root2→child4→child3，均COrderInstance/vt2A026E8、executing=false。4的rawtype1/fallback0/path[7944,5097]；3的rawtype2/fallback0/path[2072,7944]；两者+119均0。此次六实例均已直接确认停止，不再仅声称根列表全部。新样本见t201_recursive_plan_sample.json。
根据官方10AF270确实递归+1F8/+2D0，原own_plans只扫集团三数组会漏两个实例，已修为有界/去重/RTTI检查的递归集合（最多4096实例、深度64、每子数组256），继承所属COrdersGroup军标识，并仅在evidence记录父ID，不塞未支持schema属性。未将任何子path自动命名axis、未给root空节点或fallback强套type。新路径加入只是扩展已有verified vertex字段覆盖，不增加清单字段升格。
新完整导出t201_full_capture_recursive_a/b.json，两次observation完全相同，21师、12省、2集团军、1集团军群、6计划实例（4根+2递归子）、2战斗；ratio/in_supply仍12正常/9不足。原早段4根/50缺失导出保留为历史，不是最新结果。最新全schema有52个required缺失（新增两实例各缺type），无其他错误，complete_input=false，不能称全合同成功。
54项离线回归全部通过（原50+4项递归/去重/身份/新导出）；采集前后官方暂停、speed0、日期tick60759398及6实例executing=false完全一致。CCombatManager的活体RTTI为.?AVCCombatManager@@，vt RVA29CD318，进一步确认GS+260管理器与+268数组桥。
最新接续点：1. 在现在已有真实type1/2非空子实例上追FCF8F0/12E6E20渲染及axis消费，不再拿空root1/2为样本不足理由；区分顶点线段与箭头轴线。2. 普通陆战小时链已闭合，继续147E600统计写点与133A150创建先后分析，精确起讫仍不升格。3. isolated的HQ-tooltip支线未绑定师级this，继续原因码4生产者而非读其+199/+19B。
本段未宣称任务耗尽或整项终止，仍有新线索可继续。D盘同步权限阻断保持不绕过；准确本地证明计数74/42、剩余内存30项，D盘最后确认72/44/32内存候选且本段未写。用量最近观测27.1%（此前26.6%），没有虚称已触及10pp门。全段0Post/0游戏写入/0远程调用，不读写存档、不commit/push。
