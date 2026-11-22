# t246 十二个非内存项契约核对

范围只包括 `t245_triage_29.md` 的 12 个非内存字段。17 个内存项不在本批。没有读游戏、存档、进程，没有 Post，没有改写授权、门、schema、清单或生产捕获。

清单计数保持 14 表、116 字段、3 列、87/29。production type 51。`complete_input` 仍是 false。本批晋级 0。配置字段不是内存读数。字段名存在或环境变量未设置都不等于已验证。

生产输出在 `calling/input_capture_live.py`：观察对象只写 `meta.game_time`、`meta.player_country`、`meta.speed` 和一部分 `world`。这 12 个字段都没有赋值。根 schema 仍要求 `meta`、`policy`、`world`、`feedback`。schema 注释写明形状合法不是语义证明。

可重跑核对：

```
python "钢四陆军总司令/records/test_t246_nonmemory_contract.py"
```

该测试在精确环境值 `1` 时不调用 `Backend.write`。跑完后 `kernel32` 仍未绑定。

## meta.allow_write

状态：当前行为已锁，未晋级。

来源有两套，而且不一致。

- 声明：`calling/config.py` 的 `allow_write()`。`CLAUSEWITZ_ALLOW_WRITE` 去掉首尾空白后属于 `1`、`true`、`TRUE`、`yes` 才是 true。未设置按空字符串，结果 false。
- 有效写权限：`calling/process/windows.py`。`Backend.__init__` 只有环境值恰好是 `1` 才给句柄加写权限。`Backend.write` 在调用 `WriteProcessMemory` 之前，值不是恰好 `1` 就抛 `PermissionError`。它不调用 `allow_write()`。`Proc.write` 只转发。

`scripts/phase2at_ring_resolve.py` 只把 `allow_write()` 写进 live 报告，不用它写内存。生产捕获把环境变量设为 `0`，并在 blocking check 里写明该值不由内存提供。schema 要求 `meta.allow_write` 是布尔值，没有 default 关键字。缺键会验证失败。

未设置时两边都拒绝写入。这只说明门是关的，不是字段已验证。`true`、`TRUE`、`yes`、`1 `、` 1` 会让声明为 true，同时 `Backend.write` 仍拒绝。

### 最小修复方案（未实施）

只把 `allow_write()` 收成与 `Backend` 相同的判断：环境值恰好等于 `1`，不去掉空白，不接受 `true`、`TRUE`、`yes`。不要改 `Backend.write` 和 `OpenProcess` 的条件。

兼容性：精确 `1` 仍然是唯一能通过写门的值，有效写授权不变。`true`、`TRUE`、`yes` 和带空白的 `1` 会从报告 true 变成 false，从而和实际写门一致。`phase2at_ring_resolve.py` 的 live 报告会跟着变。把环境设成这些别名时，现有 `assert not config.allow_write()` 会从失败变成通过；那是报告收紧，不是放开写入。`allow_post()`、marker 文件和 Post 门不动。

明确拒绝的方案：让 `Backend` 接受 `allow_write()` 现在的 `true`/`yes` 词表。那会扩大实际写权限，本批没有授权。

即使以后采纳收紧方案，生产捕获仍然不输出该字段。输出和清单晋级要另经父级复核，不在本批。

## 其余十一项：明确阻塞

这些项没有可执行的完整契约。本批不补默认值，不改 fixture，不把空数组或空字符串写成已观察结果。

| 字段 | 文档默认 | 实现 | schema | 阻塞 |
|---|---|---|---|---|
| meta.geography_scope | null | 无读取函数；生产缺键，不是 JSON null | meta 必填。值为 null、`{kind:global}` 或 `{kind:theater, province_ids}`。空省份数组仍合法 | 需要用户在 null、global、theater 中选择 |
| policy.stance | 未给出具体枚举默认 | 无存储、无消费者 | policy 内可选。枚举五个字符串，无 default | 需要用户选择枚举值 |
| policy.instructions | 未给出 | 无用户原文通道 | policy 内可选字符串。省略和空串不是同一语义 | 需要用户原文 |
| feedback.last_orders.order_seq | 回执账本 | 无账本 | 条目必填整数。空 `last_orders` 数组只是形状合法 | 需要真实已发命令回执。空数组是伪造 |
| feedback.last_orders.type | 回执账本 | 无账本 | 条目必填，OrderType 或另外 13 个计划命令名 | 需要同一回执中的命令类型 |
| feedback.last_orders.subject_ids | 回执账本 | 无账本 | 条目必填整数数组 | 需要同一回执中的对象。内存单位号不能代替 |
| feedback.last_orders.target_province_ids | 回执账本 | 无账本 | 可选整数数组 | 需要同一回执中的目标 |
| feedback.last_orders.plan_id | 回执账本 | 无账本 | 可选整数。schema 不接受 null | 需要同一回执。本批不改 schema 去加 null |
| feedback.last_orders.accepted | 实际落地 | 无落地账本 | 条目必填布尔 | 队列接受或超时不是 true。`command_receipt.assess_pause_receipt` 只处理暂停，并写明 acknowledgement 不是执行证明，而且不生成 last_orders |
| feedback.last_orders.error | 失败原因 | 无失败账本 | 可选字符串。省略和空串都没有定义成无错误 | 不制造失败字符串，也不制造无错误哨兵 |
| feedback.ticks_since_issue | 发出后的节拍 | 无同一会话的发出 tick 和当前 tick | Feedback 上的可选整数，缺键仍可通过形状校验 | 不能用墙钟。暂停回执模块没有节拍运算 |

`calling/command_receipt.py` 不是这七个 feedback 字段的生产者。根 schema 要求 `policy` 和 `feedback` 存在，所以生产观察对象目前通不过完整 schema。缺对象本身不是“默认空政策”或“默认无命令”的证据。
