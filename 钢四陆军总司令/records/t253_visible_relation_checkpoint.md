# t253：当前可见关系实测与 country-reference 反例（不晋级）

## 本轮确有实机工作，不是旧checkpoint复述
2026-11-22 05:26:58 EST freshguard：PID30108/base0x7ff78b690000，loaded1.19.5.0.7c6c，exe SHA256 `709f916afbebcfe64a26678702691aeb40945d206074c2a80de8e9d601fce148`，SOV/index3，pause1/speed0/tick60781105，两OPEN门false，ALLOW_WRITE/POST环境均unset。每次后续收集重新解析实际PID/base/roots，只开 **0x410** 只读句柄，不复用heap。最终失败封存时05:35:35.7636339 EST，guard仍相同；这不是未来游戏状态保证。

### 已完成的新鲜见证
05:31:05 EST 从当前GS active-combat表精确查找先前获准对象combat3072：最多32个header，实际15个，**不是拿旧unit399或owner443直接解引用**。双方当前CLandCombatant类型/回链、CArmy类型51、CCountry与CProvince类型重新核验；只取每侧首个单位，260个读取依赖逐一复读稳定，8个本问题消耗的代码窗口匹配旧指纹。

| 本次实际条目 | 两个country word | 当前国家 | 省份/overlay | 本轮结果 |
|---|---|---|---|---|
| 490，type51，attacker | +1D8=3，remap3；+1E0=3 | SOV | 1777 /255 | genuine self/nonwar控制；不冒充foreign visible条目 |
| 399，type51，defender | +1D8=368，remap368；+1E0=368 | D04 | 10544 /250 | 当前普通陆地、fog1、modifier24B缺失、双向active-war成立；原生揭示分支投影250，具名敌对关系候选enemy |

后者是**本次独立重绑恰好再次遇到399**，不是沿用旧值。当前字段中不曾使用历史443/CHI；也不把country index当固定历史tag。

方向来自已有独立具名链：`TRIGGER_HAS_WAR_WITH ->439CC0 ->vtable280BBE0 ->3F79E0`。实际D04→player3的CRelationStatus目标raw/canonical均3，+2E8是CWarRelation且+49=0；反向SOV→368的目标也独立一致。SOV→SOV为真实无war对象控制。类名、combat side和overlay本身均没有被用来命名enemy。布尔和byte均为**读到native输入后的离线投影**，不是调用引擎、原始官方schema枚举或“直接读到relation_to_player”。

同一见证中双方parent+188=0、双向+288 dependency均不存在；没有新的player-relative subject/overlord阳性。没有重采MAN→JAP、null faction或非战即友路径。

## 真正触发止损的反例：旧 owner-join 断言不普遍成立
为剩余2个条目预算读取同一当前attacker列表的后续参与者，不扫描别国/整军：
- rank1：unit4652，RTTI确为 **CArmy**，handle type却是 **4713**，严格拒绝。没有为了类名放开生产51；这类现象历史已知，本轮只是再次实测，不吹成新发现。
- rank2：unit1101，CArmy/type51。最终只封存同一对象的原始两个country word，重复读取稳定：
  - `+1D8 =16`，`+1DC=0`，当前GS remap16→16，typed country **ITA**。
  - `+1E0 =3`，`+1E4=0`，当前GS remap3→3，typed country **SOV**。

所以 `remap(int[CArmy+1D8]) == int[CArmy+1E0]` **被真实当前反例否定**。t240式收集器把前者称raw owner、把后者当其canonical owner，并要求相等；这只在399/490这样的相等样本成立，不能推广。也不能把+4整数自行当canonical cache。

**本轮未证明两个偏移各自究竟是owner/controller/original-owner中的哪一个，明确UNASSIGNED。** 不凭16/ITA与3/SOV的数值、参战侧或RTTI给它们反向命名；不就此改生产owner读取。399/490两个值一致的候选不因此自动成为完整、通用owner合同；1101没有被输出为self/ally/subject/enemy，也没有做额外visibility放宽。

## schema与不可偷换的验收边界
现有box schema SHA为 `9a941dd3931b635591582b0d2ba3fe7ab1ceb3554a2d30af54154e61071b45ee`，Relation允许：
`self, ally, enemy, neutral, subject, overlord, unknown`。
VisibleUnit明确required `relation_to_player`。**unknown合法并不意味着字段已验证**，不能填unknown把剩余表格刷成通过。

本轮有1个fresh visible/enemy候选和1个self/nonwar控制，但self并非foreign-friendly阳性；不取代既有foreign-friendly/subject对照要求。旧t224可见能力仍是窄范围见证，不是完整feed；本轮没有运行或放宽其硬编码旧样本replay adapter，也没有修改可见范围/字段语义。

因此 **0晋级**，清单仍87/29（17memory+12nonmemory），14表/116字段/3列，SHA：
`8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3`。
生产51、complete_input=false、captureclosed维持；并发云端配置接入不被本轮冒称内存晋级。

## 失败、预算和针对性测试（如实分开）
- 初始guard 1次；后续collection启动4次：2份完成封存，2次执行内断言失败，spawn failure0。
- action1：完成两条新鲜见证。
- action2：先拒绝4713，再在下一条type51对象触发 `owner join`。5个额外native窗口校验在报错前已执行，但**没有完成terminal依赖封存，不计合格的新指纹验收**；不把未输出partial rows算成功控制。
- action3：首次诊断误取rank1，在 `unit type` 处拒绝，尚未读country words。失败不删除、不冒充“无样本”。
- 两次失败后不再搜索/分类。action4仅保存**已经读过的同两个条目**，不增加候选；捕获上述确切反例后终止live。总共4个唯一entry（490/399/4652/1101），没有第五条；重复诊断不重计新样本。没有借换字段继续空转。
- 5个新增离线证据回归，1次成功suite、5次case执行、0重跑/0失败，旧套件0。检查schema七枚举、fresh敌对/自国控制、真实不等country word、RTTI不能覆盖51、尝试计数/不晋级边界。命令：`python3 records/test_t253_visible_relation.py`。这些是记录一致性测试，不是独立游戏实验或真正的foreign-friendly样本。
- 另有1次box文档装配失败：不必要的modifier-ID手工转录数量断言失败，文件尚未写入；没有以旧list顶替本次读取，改为保留成功收集器已核实的sorted/24B缺失结果而不转录列表。同个失败启动链随后找不到尚未生成的测试文件，0个case执行。两者与实际5个通过case、2次native收集失败分别记账。

## 精确后续问题，不重开已关分支
父级如交云端，问题应是：**独立审查既有schema owner合同/生产命名与CArmy+1D8、+1E0的用途，解释这份真实反例；不要未经原生具名消费者核验就换偏移或反名。** 本地native侧若继续，也只应寻独立具名owner/controller接收者及当前可见且player-relative的真实subject/friendly对照；不是继续采D04零dependency、MAN/JAP、null faction或非战即友。当前缺口是语义身份与对照，不是再多读相同负例。

## 安全、保存与提交
gamewrites/Post/nativegamecalls/saveaccess/timeadvance/pause-speed/UIchanges全部0；句柄finally关闭，0背景任务；不运行capture/doctor/status，不改仓库通用代码，不改清单、不commit/push。只做machine-specific读取和新证据离线回归。

新增仅本checkpoint、`t253_visible_relation_evidence.json`、`test_t253_visible_relation.py`，原字节增量保存：
- C权威 `C:\Users\Lenovo\Documents\钢四陆军总司令\records`
- box `/workspace/hoi4-docs-latest/records`
- Windows checkout对应 `钢四陆军总司令/records/`

只校验新增文件size/SHA，不全量hash/同步；C/box/checkout的实际回执留box工作目录。GitHub尚待父级把这3文件一次提交，不能称gitHEAD同步。没有把旧24文件、t252回执、exe、dump、存档或凭据重复打包。实际游戏exe获准正常readonly；退休D文档目录未访问。
