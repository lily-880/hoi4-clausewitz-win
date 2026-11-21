# t202 checkpoint（继续严格只读）

## 块1：会话重绑与目标调用链开段
已重读t201记录、加载code-changes，按本机活体依赖例外。机器在线；重新发现PID/base/GS/idler/country，官方暂停、speed0、六实例executing=false、闸门关闭，读前后游戏时间不变。0Post/0游戏写入/0远程调用，不推进时间、不读写存档、不commit/push，历史写入脚本保持硬禁。
本段不读取任何D盘文件（包括未重读exe文件）；新反汇编只读当前进程已加载代码/.pdata，RVA随新base绑定，记录代码段SHA。没有为完整capture绕过原exe文件指纹闸门；既有完整导出仍52required缺失、complete_input=false。
已展开FCF8F0、12E6E20、147E600、133A150完整函数/UNWIND链，证据t202_initial_chains.json与_t202_clip_*.txt。接下来追各函数的数据来源和消费，不把path直接命名axis、不把边境战计时字段套普通陆战。
本地证据74/42（内存剩30、非内存12）；D盘最后72/44，14表116字段3列，未读取/同步，pending文件保留。

## 块2：目标函数桥接、排除跨类猜测
147E600不是直接统计字段writer，而是按双方真实CLandCombatant虚表依次调用B0、98、70、100槽；活体绑定对应133F5B0、13480E0、1347CC0、134BF50，已展开真实回调而非猜offset。134BF50把对方E8/100/118单元列表按国家聚合计数，并遍历+140候选记录的+8句柄、+14整数；尚未把此整数称人力伤亡，继续追写入者。
133A150仅构造0xD8字节普通陆战派生体，+D0=-1，不自带已证明start；新直接调用者C0B8D0是正常创建链、C0DB60有token分流及序列化入口，不能把读档解析分支当正常新战创建。这里只读代码，不调用解析、不读取存档。C0B8D0会调用1FA590后交2283C60管理ID，须辨别ID分配与时间，不能见date形似数值就升格started_at。
FCF8F0的UI2/3/4分支明确把实例+70路径作为第5参数、实例作为第6参数传12E6E20，r9为0；渲染器另有r9非空的双线几何分支。实际axis是否独立字段仍须区分输入顶点与派生箭头，不能将同一+70重复命名axis。现存子4/3继续作为非空语义对照。
新读取嵌套实例几何和当前四侧+140候选记录见t202_deep_semantics.json，均为有实质新调用链的针对性只读采样，未制造时间样本。

## 块3：新官方链与反证（不冒升）
### 顶点/轴线
12E6E20的已加载.text直接call共5处，FCF8F0/FD09F0/FD5730的r9=0；FDAE20与12E1970先调10B9ED0(this,1)，再将返回实例作为r9。10B9ED0仅遍历实例+1E0的实例引用，返回首个rawtype相符者；新live有3(type2)+1E0->[4(type1)]、4(type1)+1E0->[2(type2)]，其余4实例此数组为空。与已读子数组互为方向，给出真正关联，不是+38。
新live类型核实6实例+38均指COrdersGroup（两指针），不是父计划；记录已改掉parent_ptr38误名。+8原始值53未认作group ID。所有6实例+280为空，268/270是原始定点坐标，不是province ID。渲染器RBP+280为栈上mode，不能当实例+280。由此已区分目标/前线双输入及派生箭头，尚不能把任何顶点数组重复升格axis。
### 普通战斗真正损耗路径
147E600->CLandCombatant slot98(13480E0)->1343100->真实CArmy slotC0=CEC2E0。CArmy slotF8=CE4D70读取+420，slot120=CE4D60读取+428；CEC2E0对这两值减损并钳0，累计+448/+450。1343100在调用前后取实际差额，1343786/1343794累计目标一侧+178/+180；四侧现存非零原始对为(21000,40810)、(790800,1105050)、(125100,158470)、(198000,300245)。这是HP/org受损，不是人力损耗，不能填casualties.our_manpower/enemy_manpower。
新RTTI反证：+140记录的原生vtable2A23650类型是CAirInLandCombat，writer1349780创建0x38航空支援记录并更新+10/+14；当前四侧列表为空，不等于零人力伤亡。+130现存类型是CCombatTactic；133E040加总的+138..+160是战术修正，不是损耗统计。已明确纠正候选命名，避免先前两条链误认伤亡。
普通创建C0B8D0->1FA590的临时输出明确是(type0x3E, ++GS+748) ID，非date。147C240构造+40=-1/+44=0；133A150没有普通陆战绝对起始timestamp。普通小时调度可证明计数单位，仍缺创建/首小时先后与精确绝对起讫，未移植边境战字段。
### 配送/isolated
已从加载.data RTTI与.rdata COL找到CSetArmyTemplateCommand，vt2A2D7A0。slot48=1401070检查真实师对象并在1401223调E64C50，false分支文案为“army cannot process delivery (possibly cut off)”；slot50=13FD5C0是会改模板的执行路径，均只反汇编，未调用。
E64C50先考虑Army+2F8/+2E特殊分支，再取省份+1F0->D0，与737F50的供应区域比较，否则经7362C0/EEF530/12B6690图查询寻找可达项。已完成26个真实直接调用者列表t202_delivery_callers.json，而非HQ字段猜测；但“possibly cut off”并不等价于exact isolated，原因码4生产者仍需深查。1738..1745的mov immediate4候选均非已证原因writer。CTemplateChanger本身仅6槽，之前孤立脚本越表+218候选已明确作废，绝不当官方绑定。
上述见t202_renderer_loss_bridge/t202_native_stat_axis/t202_damage_parent_links/t202_template_reason_sources/t202_isolated_binding/t202_delivery_reason_branch/t202_delivery_callers.json及对应clip；无新schema升格，本地74/42，内存30+非内存12，D最后72/44且未访问/同步。

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
