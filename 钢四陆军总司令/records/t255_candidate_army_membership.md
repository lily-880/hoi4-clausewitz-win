# t255：unit1101在当前玩家候选数组中的精确指针检查

## 实际结果：不在本次候选数组，不能泛化所有权
**2026-11-22 19:25:29 Asia/Shanghai（UTC+8）**，freshguard通过后，当前CArmy/type51/id1101指针`0x222bb7e2260`，在当前玩家SOV/3的**候选CCountry+0x290数组49个指针中精确匹配0次**。

这只回答“当前这一指针是否在当前这一候选数组”。**不等于不属于任何玩家军队，不证明+1D8是owner/controller，不因+1E0是SOV就输出self/ally。** 没有独立1.19.5具名native consumer证书，数组形状合理和字面成员结果不能替代语义证明。本轮0晋级。

## 当前连接与新鲜会话
ListMachines确认本轮发送端`049434ab-4025-49de-a510-fcc276f59ed1`是iPhone；真正连接的Windows仍为`a849f760-4114-424f-af9c-d10eef8ca3e8` / LAPTOP-6FQIF6OJ。这是本轮工具结果，不是按旧主机名猜测。

OS重新取得实际进程和模块：
- PID30108，runtime base `0x7ff78b690000`，image59387904 bytes；数字恰与旧会话相同，**仍重新解析roots和heap，不复用旧地址**。
- 实际exe `D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe`，SHA256 `709f916afbebcfe64a26678702691aeb40945d206074c2a80de8e9d601fce148`；loaded version `1.19.5.0.7c6c`。
- GS/Idler RTTI合格；player当前raw/canonical3，typed CCountry、tag SOV；pause1、speed_slot0、tick60781105，末端一致。
- 显式ReadProcessMemory句柄仅`0x410`，finally关闭。97个已登记依赖末端逐一复读一致；country tag仅辅助展示，不参与指针membership。

以上仅是该采样时刻，不保证以后游戏仍运行、仍暂停或PID/heap不变。下一次必须freshguard。

## 最小身份桥与数组读数
从当前GS active-combat数组最多32个header内查exact combat3072，实际检查15个；CLandCombat和attacker CLandCombatant RTTI及combat backlink核验。只读取该侧**exact rank2**的目标单位：primary/secondary CArmy、secondary complete-object offset16、type51、id1101均成立。没有扫描其他单位字段、没有读取别国军队名单。

本次同一目标的三个已知country word：
| 偏移 | 当前值 | 合法说明 |
|---|---|---|
| +1D8 | raw16→canonical16 / ITA | 角色仍UNASSIGNED |
| +1DC | 0 | [t254原生证据](t254_native_country_roles.md)绑定持久化键`expeditionary_owner`，不能据0猜单位类别 |
| +1E0 | raw3→canonical3 / SOV | t254绑定持久化键`logical_country`，不是单独self证明 |

候选CCountry+0x290 header24：data=`0x222be0b9ab0`，capacity63，size49，opaque alloc=`0x7ff78e78d000`（不解引用）。符合`0<=size<=capacity<=4096`，data有效；24byte signed与16byte unsigned解释的data/capacity/size一致。
- header24 SHA256：`8ccc7e1ae581fd64f8e36aa309c48c2ba567652278dbc2980b77ddc9c970add8`。
- 仅读取`49*8=392` bytes候选指针序列，前后稳定；不解引用其中任何其他unit。
- 指针序列SHA256：`d5a5ac65f0c96683ee7898275f1013c7ef00459d9315bb03c97d449c1f5c0ac8`。
- exact matching indices为空；没有用id、country值、相邻地址或remap相等代替指针相等。
- 公开JSON仅含目标、选定24byte header、392byte序列摘要和结果，**不附完整指针序列、exe、内存dump或存档**。

## 证据来源与版本证书缺口
本次候选布局由父级云端代码核对后提供：`calling/gamestate.py::_pdx_array`、`calling/input_capture_live.py:54-60`、`calling/input_observation.py:54-63`、`offsets_verified.json`。本worker没有重审这些通用源码、没有运行observe_own_divisions/旧CLI，也没有以其整表拒绝代替本检查。

**0x290早期Haiti证据不是当前1.19.5的具名runtime army consumer。** 本次仅在精确1.19.5 SHA门内沿用候选硬编码；缺口仍是：同一指纹内，从已知CCountry receiver访问+0x290并具名消费Army集合的原生运行时链，以及其类型/范围合同。没有现成精确入口，不邻域盲扫、不过度解释49这个计数、不重复负例轮询。

结合[t254范围修正](t254_owner_join_scope.md)，1101这份combat反例本次没有进入该候选数组，不能被注入生产own_units；也不推翻已限定own/self输出。完整`visible_units.relation_to_player`仍需要独立owner身份合同、qualified fresh visibility，以及真实player-relative友方/subject阳性与方向控制。literal absence不是完整字段证书。

## 新增针对性离线检查（非游戏实验）
命令，仅box运行：
```text
python3 /workspace/hoi4-docs-latest/records/test_t255_candidate_army_membership.py
```
一次suite、**3个唯一test方法、3次方法执行，3通过，0失败、0重跑**：
1. 本次24byte真实header的signed24/unsigned16双解码、49/63及392byte窗口一致；证书false仍保持。
2. synthetic size64>capacity63必须拒绝。
3. synthetic三指针fixture只允许exact pointer命中，并拒绝target+1（两个人工算法向量）。

后两项是清楚标注的**离线人工算法检查，不是真实游戏正负样本，不重演49个实际指针、不构成owner语义证明**。旧测试/云端套件均未重跑。实际live采集1次成功，0失败，没有第二次重复轮询；一旦精确membership问题已得到字面结果，就不为凑动作再读。

## 安全、清单与增量保存
本轮gamewrites/Post/native-gamecalls/saveaccess/timeadvance/pause-speed/UI变化全部0；**未读取或改动生产四pin及门**；没有capture、doctor/status、native callback、自动生成样本、全量hash或全量回归；无后台任务。退休`D:\Michael Foo\钢四陆军总司令`未访问，实际exe按正常受审只读。

本轮不改清单：87/29（17memory+12nonmemory）、14表116字段3列，沿用SHA `8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3`，不是本轮重算整个清单。production51/complete_input=false/captureclosed不放宽。

新增仅本MD、`t255_candidate_army_membership.json`、`test_t255_candidate_army_membership.py`。原字节增量C权威`C:\Users\Lenovo\Documents\钢四陆军总司令\records`、box `/workspace/hoi4-docs-latest/records`、Windows现有checkout对应`钢四陆军总司令/records/`，仅缺失CreateNew/同SHA跳过/异SHA停止；size/SHA与实际同步结果保留box单份回执，不另造回执套娃。

父级已提供PR1实际merge main=`f1dfb93096fa98af6c2eb4b211898c61a5f5a2cf`，旧checkpoint“PR1未合并”是历史状态，不再沿用。本worker未再次查询forge、未改gitHEAD/dirty。**本次manifest zip交父级从当前main开新分支/新PR提交，不追加已merge PR1；新3文件GitHub尚待提交。** 当前raw heap pointer仅作会话证据，禁止当下一轮输入。
