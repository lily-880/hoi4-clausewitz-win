# t197 checkpoint

授权：`pt183u`（把剩下的字段全部验证好，不要停下来）+ `pt180u`（写入/代下最小指令）。每次 Post 后关闸；只允许暂停/1x；未写存档；未 commit/push；未对师句柄再发 CSetArmyLeader；未从工厂对象 +0x8 整段清零。

## 会话（结束时需再确认）

- machineId `a849f760-4114-424f-af9c-d10eef8ca3e8`，LAPTOP-6FQIF6OJ，始终在线。
- pid **12948** 全程存活，未崩溃。版本 Windows 1.19.5.0.7c6c，SHA256 `709F916AFBEBCFE64A26678702691AEB40945D206074C2A80DE8E9D601FCE148`，base `0x7ff7a91c0000`。
- 开段与 t196 结束一致：ETH，1936-01-01 13:00，官方暂停 +0x6c1=1，速度档 0。本段未再开 1x，日期应仍为 13:00。
- 闸门在每次 Post 与失败退出后均关闭，`allow_post=false`。

## 本段实际发出的命令

1. **COrderGroupCommand**（factory 0x18d0140）：师 1846（12757，内陆，非 1829/1838）。IsValid=1，`post_rax=1`，`wait=0`。新建集团军句柄 **{53,411}**。未任命将领。
2. **COrderNewRootCommand**（factory 0x18d0440）：在集团军 411 上打包 +0x48/+0x4c = PE 文件里的 380896/380934。IsValid=1，`post_rax=1`。得到计划实例 **id=2**，type=2，官方 path +0x70 为空，+0x258/+0x25c 恰为 380896/380934，`can_execute=0`。未执行该计划。
3. **COrderSetPathCommand**（新定位工厂 0x18d0950，size 0x58，VT 0x2A84FE0，IsValid 0x18dff70，Execute 0x18daf60→0x18e5f60→**0x10b0d90**）：对实例 2 打包路径 2072/7944 后 **IsValid=0，未 Post**。
4. 再次 **COrderNewRootCommand** 干跑：按活体 SetPath 哨兵打包 +0x48/+0x4c=0,0。**IsValid=0，未 Post**。

未重试已失败的 SetPath Post（根本没有发出）。未改计划 1，未对师句柄发任职，未 5x，未拆建筑，未开战斗。

## vertex_province_ids：官方写入路径已找到，但入口互相卡住

- 官方 path 数组仍是 COrderInstance+0x70（writer token 0x174）。拷贝函数是 **0x10b0d90**（`lea rdi,[rbx+0x70]` 后调用 0x1f7640）。
- t196 的 COrderNewFrontCommand Post 成功却不出现新实例、+0x70 仍空：Execute 0x18d9070 先调用 **0x10b8620**，输出数组 size 为 0 则跳到 0x18d99af，**到不了 0x10b0d90 / 0xc41bb0**。0x10b8620 对父实例走 0x10bb5a0；父实例 +0x298/+0x299=0、+0x2ac=0，且 +0x258 不是活体空哨兵时会走 0x2284870，结果为 0。
- **COrderSetPathCommand 是把路径写入已有实例 +0x70 的官方命令**。Execute 在 flag 条件下直接调用 0x10b0d90。IsValid 要求实例 +0x258/+0x25c 等于 **运行时** `[0x33EB2A0]` / `[0x33EB2A4]`。
- 这两个常量在 PE 文件里是 380896/380934，但 **本局活体已被清成 0,0**。因此把 PE 常量写进 NewRoot 后，SetPath IsValid 必然失败（诊断已确认 0xbbb250、0x2284870、0xc402a0(id=2) 都能工作，失败点就是哨兵比较）。
- COrderNewRootCommand 的 IsValid 比较的也是 **同一对** 0x33EB2A0/A4 活体值：+0x48/+0x4c 不得同时等于该空哨兵。活体空哨兵是 0,0，所以 NewRoot **拒绝** 0,0，而 SetPath **要求** 0,0。两道官方门在本局互相排斥，无法用「先 NewRoot 再 SetPath」做出 +0x70。
- 0x10b0d90 的直接调用者还有 0x18d1150、0x18d6660、0x18e5f60、0x18d9070。其中 0x18e5f60 属 SetPath，0x18d9070 属 NewFront；0x18d6660 看起来会 `0xc41720(edx=2)` 新建实例并把命令 +0x48 拷到 +0x70，但尚未绑到可打包的工厂/IsValid（可能是共享 helper）。在没有安全配方前不盲目 Post。
- **不把 +0x258 当官方 vertex/path，本段不升格 `world.plans.vertex_province_ids`。**

## 其他剩余字段

### 12 个非内存字段（不升格，也不为此停工）

`meta.allow_write`、`meta.geography_scope`、`policy.stance`、`policy.instructions`、`feedback.last_orders.*`（6 项）、`feedback.ticks_since_issue`。清单已写明由配置或回执账本提供，不是内存发现。

### plans.type

活体仍为 2。GetOrderType 仍只命名 1=ORDER_MOVE、3=ORDER_INVASION。UI 跳表对象的 +0x90/+0x224 与当前 COrderInstance 对不上（+0x90=0，+0x224=32759）。无新的官方命名对照，不升格。

### plans.axis / status

本段未找到可独立读写的官方非空对照与最小 Post 配方，不升格。

### own_units.order.type / target / eta

本段未再开 1x：计划 1 仍在执行（+0x248=1），按硬性约束不能在 Execute 之后用 1x 去跑计划。1829 路径仍在，但 t196 的一小时对照里 commandlist / full_path 仍空，+0x240=0x000041a0 不是 0-1 进度。不升格。若下一段要做 1x，应先对计划 1 发可逆的 `COrderExecuteCommand execute_order=0`，再短暂开 1x。

### leaders.assigned_to 的 unit 种

未再对师句柄发 CSetArmyLeader。本段没有只读证明「+0x1048 也可指向师」的安全样本，不冒险补任职。

### 战斗 / 补给 / FoW / 危机 / 缺口

- `GS_COMBATS`（offsets 0x268）本局为 data=0、size=0 的空表。ETH 虽与 ITA 开战，13:00 暂停下没有陆战对象。空表不得写成 in_combat=false 或无战斗。未为造战斗而突击前线。
- 补给 / isolated / 比例：t190 边界仍在（无可靠 in_supply token，不得发明 0–1 比例），本段无新对照。
- visible_units / spotted / confidence：陆上 FoW 边界仍在（already_spotted 是海军任务），不把外军当玩家可见输出。
- crises：无对上 schema 的官方常驻危机表。
- wars.front_invalidated：无具名 token。
- shortages.*：装备 77 轨迹已关闭；人力官方缺口公式已知，但本开局师级 current=need，无不满员对照，不把 0 升格。未故意打残师、未拆建筑。

## 升格

**本段没有新的清单升格。** 已升格字段全部保留。清单仍是 14 表、116 字段、3 列，**64 已验证 / 52 未验证**，SHA256 仍为 `a159657f42fa0ec4ab65e7342473c7a4432a763d91d378ff07c37b2059f5a4d2`。

## 停止状态与下一步

- 进程 12948 应仍官方暂停、速度档 0。脚手架：1829 路径 5010→8036；集团军 1 + 集团军群 2 + 计划 1（executing，scheduled_member=1838）；**新集团军 {53,411} 成员 1846，实例 2 带 PE 哨兵 380896/380934、官方 +0x70 仍空、未执行**。将领任职仍空。
- 建议下一步（均可独立推进，不必再问）：
  1. 继续给 0x18d6660 / 0x18d1150 绑工厂与 IsValid，只在集团军 411 上做干跑，确认能否绕开 NewRoot/SetPath 哨兵死结并写出 +0x70。
  2. 若要做 order.type/target/eta：先对计划 1 写回 execute=0，再对 1829 短时 1x，一有非空 commandlist/官方 eta 立刻暂停。
  3. type 仍等官方命名；axis/status 继续在 writer/读者里找；战斗等前线自然出现或有极小接触再取。
- 本段没有崩溃，没有离线，没有把用量当成停工理由；vertex 卡在官方入口互斥，不是「把整段工作停下等用户」，检查点只是如实记下界限并留下已建脚手架。
