# t254：原生 country 字段具名绑定与当前混合国家见证（不晋级）

## 实质新增结论
本轮不是复读checkpoint：同版本1.19.5.0.7c6c的**实际消费token**和精确序列化/解析接收者证明：

| complete CArmy 偏移 | secondary(+0x10)偏移 | 消费token/原生持久化键 | 限定结论 |
|---|---|---|---|
| +0x1DC | +0x1CC | 0x2EDD / `expeditionary_owner` | 原生持久化字段名已绑定，不是+1D8的canonical cache |
| +0x1E0 | +0x1D0 | 0x3410 / `logical_country` | 原生解析器、序列化器双向吻合；不能直接等同schema owner/controller |
| +0x1D8 | +0x1C8 | 本轮未取得具名owner/controller合同 | 独立具名INTEL_DIVISION_REVEALED链使用的country比较操作数；角色仍UNASSIGNED |

`C58600`的R14是CArmy secondary receiver；`C594B1`比较token3410，`C59605`走精确国家查找763E10/763EA0，`C5966E`写secondary+1D0。继而沿既有`CED2E0 -> C5C0A0`**真实调用边**解码：`C5C26D/+1CC -> C08170 -> C5C284/token2EDD -> C5C28C/writer`；`C5C291/+1D0 -> C08170 -> C5C2A3/token3410 -> C5C2AB/writer`。注册表只读两个实际消费键，不做字符串普查。以上方法仅分析，**从未调用、访问存档或执行加载器**。

C5C0A0完整1392字节由同指纹live prefix128与exe精确continuation1264拼接，**从函数入口解码**，不是把续片中间字节当指令；336条入口可达指令，直接控制流不越界，call保持opaque。完整body SHA `3223c5b6a5f11bf12e4f0349b9e3d78178adcf0b0bc30703b23f994eaa055930`。公开JSON仅选中指令与摘要，原始字节不上传。

还跟进实际entry调用`C5C0BC -> 22858A0`：精确unwind二分16步，完整函数237字节SHA `cf6e533db0c8f98e292b85df5f950c04d47ca68a13c852637130fcf9e974f527`。直接对象读取仅secondary+8/+C（type/id），没有新的owner语义；其opaque helper不被宣称“绝无其他作用”，不继续盲跟。F4CA30是另两个非country序列化字段，亦不追邻域。

## 当前真实样本，不把国家数值反向命名
2026-11-22 **06:01:05 EST** fresh minimalguard：PID30108/base0x7ff78b690000，loaded1.19.5.0.7c6c，exe SHA `709f916afbebcfe64a26678702691aeb40945d206074c2a80de8e9d601fce148`，player SOV/3，pause1/speed_slot0/tick60781105，两OPEN门均不存在。仅0x410句柄，roots/类型/依赖重新解析，220个依赖复读稳定；这不保证未来状态。ALLOW_WRITE/POST本轮未重读，不能把t253的unset冒称当前重验。

只从当前GS combat3072（最多32个header）经typed attacker与combat backlink，精确rank2重绑**一个**CArmy/type51/id1101；没有沿用旧heap、旧unit399/443或按国家普查。
- +1D8 raw16，当前remap16→16、typed country **ITA**。
- +1DC **0**（本轮此时重新读取）。
- +1E0 raw3，当前remap3→3、typed country **SOV**。

故旧`remap(+1D8)==+1E0`假设确不通用；更不能把+1DC解释为canonical缓存。**但ITA/SOV差异、logical_country、expeditionary_owner=0都不足以断言本单位是志愿军、谁是实际owner或controller。**

### 同一新见证的定向国家与渲染输入
本轮另读精确ITA→SOV、SOV→ITA两对关系，各自CCountry/CDiplomacyStatus/CRelationStatus类型和目标country引用吻合。两方向parent+188=0、level缺失、relation+288 dependency缺失、+2E8 war relation缺失；按已证`3F9E40/PUPPET_OF`、`3FA270/SUBJECT_OF`和`3F79E0/HAS_WAR_WITH`分别离线投影均false。**非战不等于盟友、中立或friendly阳性**；这不是重采MAN/JAP或D04负例，也不再轮询此新负例。

同一单位kind0，province12595、普通陆地geometry1、fog1、overlay255，player modifier表79个ID有序唯一且0x24B缺失。原生普通陆地base≤250、overlay255主导、modifier加0，揭示byte离线投影255。这是当前**原生渲染输入/byte的窄见证**，不是扩展既有accepted visible-feed、不是CO_ARMIES成员证明，也没有输出schema owner/relation。当前无player-relative subject/friendly阳性，不能仅凭渲染可见和self/enemy控制晋级完整字段。

## 云端范围更正必须保留
参见[t254_owner_join_scope.md](t254_owner_join_scope.md)：坏相等断言只在临时`t240_current_owner_directional_operands.py`，不是生产own_units谓词。封存生产仅对来自player **CO_ARMIES**且+1E0==player的项输出owner/self。**1101只已证明attacker成员，尚未证明属于CO_ARMIES；不能撤销已限定的own/self能力，也不能把combat单位注入own_units。** 本轮不重复通用源码审计、不改偏移、生产代码或清单。

## 计数、止损与未采纳来源
- 本批**6次native证据动作：4次成功live、2次成功exe-only**；0次失败native采集。唯一当前army样本1个，重绑不重计新单位。
- 动作1：解析器/token logical_country与typed反例；2：精确两个serializer callee窗口；3：exe-only精确续片；4：两个消费token与3个小runtime窗口；5：当前单一样本的国家方向及渲染输入；6：exe-only精确base serializer237字节。
- **新增测试0、case执行0、旧/云端套件重跑0、晋级0。** 离线反汇编/直接CFG分析不是新测试套件。云端3个已过离线测试未重跑。
- 非native研究失败另记：1次localisation query超过35匹配自设上限，主动不输出；1次box文档文件名查找miss，随后窄查实际t253文件名。不是native采集失败，不隐藏或算成功样本。
- 已有partial t197/t199缓存未给出owner/controller/volunteer入口，不代表全映像无词。单位说明没有获得独立运行时角色消费者。最后国家样本与base serializer两次跟进均没有新增runtime owner/controller语义，关闭此**序列化入口**，不再盲跟helper/相邻或负例轮询。
- 一次公开搜索见[旧Steam讨论](https://steamcommunity.com/app/394360/discussions/0/1696045708655885735)，含logical_country但owner/control说法含糊，版本不符；关于设置/存档修改与重启的内容不采纳，未执行。不是1.19.5语义证据。

## 精确后续交接，不要求用户再说继续
请父级云端从**已审计上下文**只提供CO_ARMIES实际数值偏移、数组/count/stride布局及native证据引用（无需再审通用owner源码或修改代码）。本地worker即可freshguard后对已重绑1101做**精确指针成员检查**，不列整军名单。若云端另有独立**具名原生runtime owner/controller消费者**，提供该入口引用而不是凭生产变量名下结论。当前缺口是owner角色合同、exact own-array成员及player-relative friendly/subject合格对照，不是研究授权不足；用户持续授权仍有效。

## 边界与保存
清单仍**87/29（17memory+12nonmemory）**，14表116字段3列，SHA `8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3`。production51、complete_input=false、captureclosed保持。schema relation七枚举不变，unknown合法不算通过。

gamewrites/Post/native-gamecalls/saveaccess/timeadvance/pause-speed/UI变化全部0。0后台任务、句柄finally关闭；不capture/doctor/status，不访问退休D文档。只对OS给出的实际exe作正常受审只读。生产四pin未修改，未无意义重算四hash。最后live guard为06:01:05 EST，06:02:45 EST动作6仅exe文件读取。

新增仅本MD与[t254_native_country_roles.json](t254_native_country_roles.json)，按原字节增量保存C权威`C:\Users\Lenovo\Documents\钢四陆军总司令\records`、box `/workspace/hoi4-docs-latest/records`及Windows checkout对应`钢四陆军总司令/records/`；具体size/SHA与结果见box增量同步回执。3个并发云端record已在commit `024add9ad33296e63c5cba96bcfa22b389df85ba`，仅同步缺少本地副本，不重打包。**本轮新2文件GitHub尚待父级云端提交，不能说全同步、main合并或localgitHEAD对齐。** 不附exe、raw memory字节、存档或凭据。

历史证据入口：[t253 checkpoint](t253_visible_relation_checkpoint.md)、[t253 evidence](t253_visible_relation_evidence.json)、[t243 parser](t243_secondary_base_parser.json)。上述历史不是当前额外样本。
