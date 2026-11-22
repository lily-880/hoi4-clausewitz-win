# t256：两条候选入口止损；识别musicplayer同偏移假线索

## 新增实质证据，而非再次轮询1101
2026-11-22 **19:32:10 Asia/Shanghai（UTC+8）**，仅从OS给出的实际exe作只读核验，SHA256仍为`709f916afbebcfe64a26678702691aeb40945d206074c2a80de8e9d601fce148`。本轮不需要新live数据，故**没有重跑guard、读取游戏内存、轮询1101缺席**。

在六份定向已有native证据文件中，唯一`+0x290/+0x29C`匹配是[t226容器](t226_named_national_manpower_consumers.json)9583–9615行、旧函数窗口1925690内的1928EB4分支。对精确同指纹exe只读三个实际引用字符串，证明它们是：
- 2A8BAD0：`musicplayer_button`
- 2A8BAE8：`MUSICPLAYER_CLOSE_PLAYER`
- 2A8BB08：`MUSICPLAYER_OPEN_PLAYER`

新64byte caller窗口SHA `00d51710e88aac309ddf5dd656f66862fc8e18146a65cdeb49d95c19e29ca038`与旧链吻合：
```text
1928ECB  mov rcx,[rdi+40]
1928ECF  mov rax,[rcx]
1928ED2  call [rax+B8]
1928ED8  mov rcx,[rax+290]
1928EDF  call 183FFB0
```
**这里的RAX来自UI间接返回值，没有CCountry类型绑定；上下文是音乐播放器按钮，不是army语义证书。** 不能只因偏移也叫290，或记录容器文件名含national_manpower，就拿来补国家军队数组证明。本轮不擅自命名该返回对象具体类型。

## 两个具体候选入口及关闭理由
1. **缓存具名CSetArmyLeaderCommand IsValid / 18E0540**。来自现有t197索引指向的`research/_t194_clip_CSetArmyLeaderCommand_isvalid_0x18e0540.txt`。完整已缓存direct body是命令+28/+30 handle解析、后续资格谓词；没有已绑定的CCountry+290数组遍历。名字/当前版本绑定本轮未独立重证，不把缓存标签当新证书，不盲跟无名callee。关闭这个入口，不声称所有opaque callee绝不访问军队。
2. **实际同版musicplayer_button / 1928EB4**。上述精确字符串和代码窗口已新核。最初exe-only采集尝试未取得callee183FFB0的exact unwind入口，报错退出；随后将范围收窄为实际引用字符串和已知caller64，完全不读未知边界callee、不追邻域。此入口因wrong/unbound receiver和音乐UI语境拒绝作为army证据。

额外只查询已有partial t199字符串缓存：army-count模式0命中；army/division宽一点的缓存查询仅9条，实际均为define、army-group命令UI或border-war词，没有合格country→army消费者。t197仅提供上述cached命令入口。**这不是全映像无词结论，也不应重复查询同一partial缓存。** 六份box证据定向检索亦不等于全库普查。

## 诚实计数与证书缺口
- 两个exact候选入口已关闭；EXE-only采集2次启动，1次完成、1次边界断言失败；失败不算成功证据。
- live guard0、live采集0、membership重复轮询0；新增测试0、旧套件重跑0、晋级0。反汇编是分析，不冒充测试或游戏实验。
- [t255](t255_candidate_army_membership.md)19:25:29的49指针数组、1101字面不在其中的结论保持原有**时刻与候选范围**，没有新的全局不存在结论。
- 仍缺同一1.19.5指纹内**真实具名registration/consumer→独立typed CCountry receiver→+290 header/count/stride→CArmy元素身份和范围**的完整链。旧Haiti样本、生产硬编码名字、数组形状和字面负例都不能补上。缺的是入口证据，不是用户未授权继续。
- +1E0仍仅已具名logical_country，+1DC为expeditionary_owner；+1D8不猜owner/controller或志愿军。不能由logical SOV输出self/ally。

## 安全与保存
0gamewrite/Post/native-gamecall/saveaccess/time/pause-speed/UI变化；生产四pin和gates均未访问，0后台任务，未作全模块/全进程普查、未调用callback，退休D文档未访问。实际exe按正常受审只读。

清单仍87/29（17memory+12nonmemory）、14表116字段3列；沿用SHA `8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3`，未全量重算；production51/complete_input=false/captureclosed不动。

仅新增本MD及`t256_army_consumer_entrances.json`，C权威`C:\Users\Lenovo\Documents\钢四陆军总司令\records`、box `/workspace/hoi4-docs-latest/records`及现有checkout对应records原字节增量保存。manifest包只含这2份新记录，**不重复t255包，不追加已merge PR1**，交父级统一当前post-merge分支/PR；GitHub尚待提交。实际size/SHA同步结果仅一份box回执，不制造回执套娃。
