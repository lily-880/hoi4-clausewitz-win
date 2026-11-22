# t249 checkpoint：ready-for-plan 已绑定本版原生回调，但关闭为 plans.status 来源

## 实质结论（2026-11-22，EST）
本轮不再停在公开方法建议：已把 **1.19.5.0.7c6c** 的精确名称 `unit_ratio_ready_for_plan` → 注册构造器 → `std::function` 实际计算回调 → scope 适配 → 两计数器计算及一条真实多成员聚合分支串起来。

它是 **CFixedPoint 比率结果，不是已证明的单个 COrderInstance 状态**。已见实际嵌套成员循环及“符合谓词数/纳入计数成员数”输出，没有确切计划 ID/归属桥，更没有独立状态枚举语义或真实正反例。因此**关闭本变量作为 world.plans.status 晋级来源**，不把 0、1、比率阈值或无成员当作 executable/blocked/stalled/invalidated。不是“所有 plans.status 方法都不可能”，也不是完成了整个 readiness 算法。

字段晋级 **0**。清单仍 **87/29（17 memory + 12 nonmemory）**，14 表/116 字段/3 列，清单 SHA256：
`8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3`。
生产 51、complete_input=false、captureclosed 原样。未修改清单、生产文件或安全门。

## 证据链及独立性限制
完整的本轮指令/窗口哈希摘要见同目录 `t249_ready_for_plan_evidence.json`；只含小窗口反汇编与哈希，不含 exe、存档、内存 dump 或凭据。此前公开方法及第三方来源见 `t248_public_method_ready_for_plan.md`。

1. **同版确实存在**：精确名称在本版 .rdata 中仅一处，RVA `29D1C70`；描述 `29D1C48` 为 `ratio of units that are ready for plan`。精确 RIP-LEA 交叉引用仅 `7171D`。
2. **不是邻接词猜函数**：注册段 `7171D` 构造该名称，`7173D` 调 `C5C8F0` 构造函数包装，`7176C` 以 `1D8D20` 配对包装与描述，`71787` 经 `1B8840` 配对名称与函数描述符。实际检查两包装复制逻辑，而非把相邻注册器误认成目标。
3. **精确回调身份**：`C5C8F0` 写入 vtable `29D41F8`；COL `2D4B290`、type descriptor `32D6EF0` 给出：
   `.?AV?$_Func_impl_no_alloc@V<lambda_49>@@VCFixedPoint@@AEBVCEventScope@@HPEBVCScopedVariable@@@std@@`。
   slots 0/1 都是 `C7F0A0` 的平凡复制函数，只算一个实现；slot 2 才是计算回调 **C806E0**，未调用它。
4. **receiver 纠错**：RTTI 证明的参数是 **CEventScope const&，不是直接 CUnitLeader 指针**。入口 RDX 是隐藏的 CFixedPoint 输出地址，R8 是 scope。`57CBD0` 解析 scope+50 的 handle，经 `2284870` 和 `1023F50` 适配；空时另尝试 scope+60 对象的虚调用 +E8。被选对象有 `+E7C <= 1` 检查，但本轮不擅自命名这个字段/枚举。
5. **输出算术独立可见**：两个局部 int 计数器分别在 stack+58（分母）、+48（分子），地址对送入 `C5FCA0`。分母为 0 时输出 raw 0；非零路径含两计数转有符号 64 位、100000 定点缩放及 `idiv`。异常算术分支是 `mov eax,0xffffffff; mov [rbx],rax`，得到 raw **0x00000000ffffffff**，不能口误成 signed -1，更不能认作状态枚举。这里描述真实 64 位指令，不承诺任意大计数的无溢出数学恒等式。
6. **实际聚合而非只凭名字**：`C5FCA0` 重取同一 scope-derived 对象，检查其 +1048 handle。在已读取的一条分支中，解析出的 container_A 的 `+230/+23C` 指针/数量进入外循环，container_B 的 `+50/+5C` 进入内循环；对符合条件的成员经虚调用取对象，调用 `CD4FD0(...,0)` 后条件递增分子，独立递增分母。这个代码分支确实处理多个成员，不是找到一个 COrderInstance 并读状态。

公开文档把该变量列在 **unit_leader scope**；该网页没有可核实的本版版本标识。本轮本版 token/回调已经独立定位，但**没有穷尽证明本版注册表所属 scope、没有实时 leader/国家归属对象样本，也没有给 container_A/B 独立绑 RTTI 类名**。不以第三方 scope 取代这些缺口；以上结论限于注册的具名比率与已见原生聚合计算，不扩张为完整 leader/group/plan feed。

## 有意止损，不再补空扫描
- `C5FCA0` 的 .pdata 初始范围只覆盖 74 bytes，条件分支跳出该范围；本轮按实际跳转读取其后续，**没有把单个 unwind 范围误称完整函数**。
- 已读聚合分支及公共返回；另一分支 `C5FE0B` 未展开，`CD4FD0` 谓词本体未读，更未调用。因已足够否定“已证逐计划状态来源”，不为追齐整个 readiness 算法扩展无关工作。
- **真实计划状态阳性 0、阴性 0**；没有完整 units、计划普查、空计划轮询或样本制造。注册存在和代码分支不是游戏值阳性。
- 本变量到此关闭。另一路若要晋级，仍须独立具名的逐计划状态 consumer、当前 exact COrderInstance ID/成员桥、自然正反例及对应测试；本轮未找到这个桥。不重开 t244 combat-ID、t245 isolated 或其他已闭合邻域。

## freshguard 与严格只读
初次完整指纹 guard：04:34:06.5768899 EST；本轮后续 live blocks 04:39:23、04:40:19、04:41:30、最终 **04:42:17.1044821 EST** 各自从当前 module base 重解析 roots。
- 当时 PID30108，base `0x7ff78b690000`，loaded version `1.19.5.0.7c6c`。
- 本次 exe SHA256：`709f916afbebcfe64a26678702691aeb40945d206074c2a80de8e9d601fce148`；OS resource version 1.0 不替代 loaded game version。
- player SOV/index3，pause=1，speed_slot=0，tick 前后均60781105；roots RTTI 及两门 closed 通过。
- 仅 OpenProcess **0x410** + ReadProcessMemory；所有句柄 finally 关闭。以上为采证时现场，不是今后会话常量，**不得复用 heap 或断言游戏今后仍运行**。
- gamewrites/Post/nativegamecalls/saveaccess/timeadvance/pause-speed/UIchanges 全为 **0**，无完整capture，无 commit/push，无背景任务。

## 成本、失败与测试的真实计数
- 成功定向证据动作 **6**：精确名称查找；精确 RIP 引用；构造/描述包装；vtable/计算slot；回调及scope/counter前段；counter后续及直接适配叶。
- 另 **1** 初始 guard；**1** PowerShell parser 失败启动（执行前，无采样）。合计 **8 次 collection launch**，不是8份新语义证据。
- 前两个精确查询实际分别读取 .rdata **9,928,704 bytes**、.text **41,434,624 bytes**。这是一次性、section-sized 查找，不伪称总共只读256字节；未保存 section/整映像。此后仅针对已知 RVA 小窗口、.pdata 二分条目，无第二次 section 扫描。
- 初版构造器自动识别因中间 +38 清零指令而返回 null 一次；离线反汇编纠正，不当成引擎不存在，也不另计一次成功证据。
- 路径上每次成功动作都有新身份或计算语义证据，连续“无新证据”=0；绑定出聚合后立即关闭，没有借新字段无限续扫。
- 新增离线证据回归 **4 个唯一 case、4 次 case 执行、0 重跑、0 失败**，成功 suite 运行1次。另一次本地启动因 `python` 不存在而在写文件/运行 case 前失败，改用 `python3` 成功；失败启动不冒充 case。
- 四 case 检查：精确注册绑定；functor/receiver身份；双计数定点输出；嵌套成员计数及只读边界。命令：`python3 records/test_t249_evidence.py`。这些只是**记录证据的一致性回归**，不是独立引擎实验、真实状态控制或生产测试。不重跑旧测试。

## 保存、提交状态与接续约束
本轮新增仅此 checkpoint、`t249_ready_for_plan_evidence.json`、`test_t249_evidence.py`；与尚未 GitHub 提交的 t248 单份方法笔记合并为一份最小包。具体目标路径、字节、SHA256 在包外/包内 manifest；只校验这几份新增文件，不做全量同步。

权威根：`C:\Users\Lenovo\Documents\钢四陆军总司令`；box 镜像 `/workspace/hoi4-docs-latest`；Windows checkout 的对应目录为 `钢四陆军总司令/records/`。保存回执 `t249_sync_receipt.json` 在 box 工作目录。异字节同名文件不得覆盖。退休 `D:\Michael Foo\钢四陆军总司令` 不访问；实际 D 盘 hoi4.exe 正常只读属于已授权范围。

**GitHub 尚待父级 CloudAgent 提交**，不能把 C/box/checkout 文档字节一致称作 gitHEAD/main 同步。既有 t244—t247 的13文件不重复入包；不带私有原始代码片段文件、exe、dump、存档、秘密或额外历史附件。没有修改通用仓库代码。此有界问题已结论返回，所有研究句柄/后台工作结束；不自动复活已关闭路径。
