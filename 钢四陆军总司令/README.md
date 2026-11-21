# 钢四陆军总司令：权威文档工作区

自用户t195u指示起，C:\Users\Lenovo\Documents\钢四陆军总司令 为以后维护最新文档的权威位置，清单文件为态势信息读取能力清单.md。D盘旧路径弃用但不删除，严禁再读取、写入或换工具访问D；不再安排向D同步。

## 最新状态
- 清单14表116字段、恰好3列，79已验证/37未验证；原D表最后72/44只是历史记录。
- 从允许C目录的t196完整64/52基线（SHA256 a159657f42fa0ec4ab65e7342473c7a4432a763d91d378ff07c37b2059f5a4d2）恢复所有116行，按t198七项、t199一项、t201补给两项已接受证明合入；未凭空新增字段或重新验证游戏。字段名、顺序和分表保持不变，说明精简为一句。
- supply.ratio/in_supply已合入本C清单；records中的原pending文件保持原文，applied=false仅指旧D未同步，不代表本C未合入。isolated等未证项不升格。
- t206 CLI补丁已实际应用，17项Windows离线测试通过；真实capture仍未验收，complete_input=false，两份既有完整fixture仍有52 required缺口。CLI-Anything参考revision34f519533bc175d2fe287ab8316b0dd99bb9cc43。
- capture SHA256 e10bf427df1059c3f16873960bcbdabef826ef1dc058ad5e087b5a67d8087d37；测试文件Windows原始SHA256 94d73593392072ab42d8749b0d4e7bfcc9d342b7514cf58cfd17cb53e01963ad。
- 研究证据仍保留在C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win\research，代码/项目布局不迁移；这里只保全必要文档与pending证据，不复制临时研究文件树。

## 关机与恢复边界
本次仅文档迁移及文档结构/SHA核对，无新游戏验证、测试、进程访问、Post、远程游戏调用、时间推进、存档读写、commit/push。任务保持停止，用户明确继续后才能恢复；必须重新核对用量、PID/base与官方暂停/计划/闸门，不沿用旧地址。最后已知现场是t205的pid12948、1936-01-02 15:00、tick60759398、六计划false；不是本次现场核验。暂停事故严格只读与历史写脚本硬禁未解除。用量最近28.7→36.9(+8.2pp)，未新测。

records保存基线、迁移所据历史证明、原pending、已更新关机检查点和补丁应用记录。box备份：/workspace/hoi4-docs-latest/。

## t207 新会话只读进展
用户pt199u/pt200u已明确继续，并授权新段用量基线40.5%至约50.5%。当前已只读重绑SOV新会话；未改变游戏暂停、速度或命令。依据49个己方师的独立人数表复核、CC6480官方缺口getter和6个非零正例，新增验证world.shortages.manpower.affected_unit_ids；缺口不是累计伤亡，8504仅现场审计合计，不升格国家needed/deficit。研究5项窄回归实际通过；17项CLI与135项t205测试仍为既有记录，未重跑。生产capture仍未验收，旧52缺口不代表新会话完整采集成功。

## t208 只读进展
新增官方行军终点字段验证：35个有效身份师、10个空路径省略、3个未证身份与491的排队分支拒绝；12项新增窄离线回归通过。清单76/40、14表116字段3列，SHA256 5926dcf451c5aef70300acbabc5421375fe5fe6e62b53da4e30f9216a4e6b1bc。历史GameDate格式链已闭合，ended_at仍缺活动/历史ID桥；ETA官方整路线计算链已找到，但当前缓存无正例、速度/寻路依赖仍待复现。生产capture未运行，52 required仅为旧fixture事实。严格只读与D永久弃用不变。

### t208 Block9只读接续
当前76/40；491真实排队命令目标10696与当前路径终点12679不同，pending非current，未升格order.type/eta。C552D0已证明先出队再vf48再销毁；CDBE50速度核心709指令已留档，后续追C55DF0/C570E0/CE6070等。最后现场2026-11-20 00:06:58上海时间，SOV6496官方暂停、速度槽0、0计划、双门闭；未运行生产capture。完整范围和纠错以records/t208_checkpoint.md Block7-9为准。

## t209 最新只读进展
新增验证order.eta的progress子字段：仅无排队普通陆地当前一跳归一化进度，35个非零正例；不含hours或全程/未来队列完成度。30项窄离线回归实际通过，35个eta子对象通过局部schema，不代表完整capture通过。清单77/39、14表116字段3列，SHAdfb6473aeb0ad9781538799440264c368e4f29dd65d444af516ade9875499ef3。官方注册已证明mode2=move_priority/player_order，不是命令类型；+1E8是独立省份目标分支，不是战斗指针。详见records/t209_checkpoint.md及证据。所有游戏写入/远程调用/存档/D/推进限制保持。

## t210 最新只读进展
新增order.type仅当前strategic_redeploy分支：9个当前正例、312项依赖稳定，18项新窄离线测试及5子测试通过，9个枚举局部校验；其他命令类型仍省略。清单78/38（26内存及12非内存未证），14表116字段3列，SHA256 1c058190f7df7ba76267dc558ffc7c579ff566efc9930a06db714ab52a834205。t209原始样本其实已有同9个战略标志正例，其检查点“49全0”为报告计数错误，非游戏推进；详情records/t210_checkpoint.md。当前路径与战斗可并存，progress1.0不是命令完成；support_attack目标已绑定主对象+1E8，retreat/withdraw/exile字段有官方序列化与渲染消费者互证，零值分支不冒升。生产capture未运行、complete_input=false，旧52缺口不当新会话验收；D和所有游戏写入/调用/推进限制不变。

## t211 恢复与最新只读进展
实际进程通道已恢复，早前5份JSON逐字节保全，box待存Block2已合入研究及records。新证仅world.combats.phase的两场普通陆战ongoing（3096/3097），ended及其他场次仍省略；官方管理器、交战资格及双方终止谓词链已闭合，非只看finalized。18项新窄离线测试通过，box回放同18项亦通过；不是重跑旧17CLI/135项。额外证明4713/4652经官方哈希注册表及RTTI的+10基址调整解析为CArmy，但生产门和当前phase检查器未改；下一块可沿此新入口继续。清单79/37（25内存、12非内存未证）、14表116字段3列，SHA256 d951b1c896ac68ad107c59272092ef43433e68f1fe3e073ea699d4cc552d330a。最后现场13:10:47 EST Nov19为SOV/pid6496、官方暂停1、速度0、1938-06-26 02:00/tick60781105、计划0、双门闭。生产capture未运行且仍complete_input=false，52缺口仅旧fixture，D与所有游戏写入/调用/推进禁令保持。最新共享周用量48.6%，40.5基线+8.1pp，50.5门未达，原授权继续有效。

## t212 只读覆盖与组引用
3072经官方扩展句柄查找、三对照与RTTI COL16的窄研究适配后独立证实ongoing；13项新针对性离线回归通过。无证明仍拒绝，生产51闸门与t211原检查器未改，也未放行全部4713。现phase只证3096/3072/3097的ongoing，非其他phase。清单仍79/37，14表116字段3列，SHA256 3e48b4d7063a928254f4aff4065fa6b003e2c4d4f2f85160ba87127e7212ff0d。6个observer内首次查到8个活动组引用，实际均为type53的COrdersGroup（5个组），组可跨多场战斗，不能当活动战斗ID。历史ID桥、伤亡及结束时间未升格。游戏及D所有只读限制、production capture未验收与旧52缺口边界不变；具体见records/t212_checkpoint.md。

### t212 Block4补充
活动组+10的9个嵌套引用实际全是type52的CReferencedDivisionTemplate（7个不同模板），不是师或战斗编号；活动组+28键值已从官方注册命名为enemy_dmg_units/enemy_dmg_str，不当人数伤亡。最后13:26:39 EST现场仍暂停1/速度0、计划0、双门闭。共享周用量实测49.2%，40.5基线+8.7pp，50.5门尚未到；本块已保全，后续按原授权做窄验证。清单仍79/37，SHA不变。

## t213 定向token读链
已只读拆明253ECD0的已初始化token名称表读链，实际9条读取/14依赖稳定、3个独立注册对照吻合；3F=group、2F50=division_template、30AB=damage。函数存在初始化与同步辅助调用，绝未调用；只读现存表，不放宽名字校验。未跑新unittest或旧套件，无新字段升格，清单79/37和SHA不变。最后现场仍SOV6496暂停1/速度0、计划0、双门闭；capture未运行。用量实测49.5%，40.5基线+9.0pp，50.5门尚未到。详见records/t213_checkpoint.md。

## t214 四个damage字段名称
只读核实298F=from、C6=receiver、2990=to、308=value，并复用原writer/parser确定SDamageDone的+8/+C/+10为三个独立国家tag，+18为value；不把它们猜为攻守方，也不当人数伤亡。未读伤害/人数值，未跑新旧测试套件、未改代码/闸门/清单。最后13:34:44 EST现场仍暂停1/速度0、计划0、双门闭，capture未运行。清单79/37、SHA不变；共享周用量实测49.7%，距50.5门约0.8pp。证据见records/t214_checkpoint.md。

## t215 独立消费者边界复核
仅复核已有文件，未找到独立SDamageDone消费者/计量单位证据，未新增现场采样、测试或升格；精确候选排除和后续所需见records/t215_checkpoint.md。本块实测49.9%，未触50.5预算线，不以凑预算扩展宽扫。

## t217 组织度损失证明及用户停工
6份t216原始JSON已完成C records/box逐字节SHA同步。新增原生+180实际地面组织度损失证明及3096/3097双方正例，34项独立新离线方法在box通过，Windows未重跑；仅升格combats.casualties组织度子项，不声称人数伤亡。清单80/36、14表116字段3列，SHA711d38a84a26929f89ecbaa0781a66e8b2061da7364da7ea9e6379b662b8fabd。188/190为prevented而非air，真实air168/170当前为0，纠错保留。按t204u下一保存点停工，最后现场仅指停工前快照；之后不再读取游戏，用户可自行游玩，等待明确继续才重绑。共享周用量52.2% vs基线50.9%，未触60.9门。详见records/t217_checkpoint.md。

## t218 新进程绑定与原生日期契约
pt205u已解除暂停与百分比停止门。新PID10288、SOV3，重新绑定堆对象，非旧PID6496地址；末次会话见records/t218_final_session_guard.json。原生CGameDate年/月/日/小时格式及365天无闰日历已闭合，20项新离线方法在box通过，Windows未重跑；月份/日志月桶键不等于活动战斗ID，故start/end时间仍未升格。清单仍80/36、14表116字段3列，SHA711d38a84a26929f89ecbaa0781a66e8b2061da7364da7ea9e6379b662b8fabd。未改生产与门、未capture；不是用量/用户停止，可直接接t219继续。

## t219 装备需求的独立缓存交叉证明
world.shortages.equipment.demanded仅按四类、空附加组件且每日缓存独立核对一致的条件升格：步兵10015、火炮147、支援121、轻坦底盘2324。新35项离线测试在box通过一次，Windows0；不推广其他类型/deficit。库存解析器对三个负FIXED桶的拒绝保留，未放宽任何生产门或输出完整契约。清单81/35（23内存+12非内存未验），14表116字段3列，SHA7e25b2f0dce3b4ff69f0ad258bf90daa94f7d8b22c72e16ce2bfe9d6738d4ee2。下一步train/motorized特殊分支，详见records/t219_checkpoint.md；pt205u持续授权，无百分比停门。

## t220 列车与摩托化特殊分支
通过实际国家映射、供给对象本国回指、工作行整数和及变体句柄精确连接，确认列车总数83、承诺计数15、原生未占用可用量68、官方额外未交付需求0；83-68的15不是缺口。摩托化特殊计数0/0，请求需求1278与缓存余额-1278一致。既有demanded字段按门/计数/缓存一致及空附加组件条件扩展至六类，没有新增字段。34项新方法通过（33个不重叠场景），Windows0。清单仍81/35，14表116字段3列，SHAb62c8bb5cd37404b28060a0820e6e7466283d4cb0f1a9cb1c535a045542479dc。未改生产或门、未capture/cloud；下一步独立余额消费者核验deficit语义。

## t221 官方签名余额消费者与缺口字段
独立消费者是后勤界面名为in_stock的控件，显示1409630当前可用减去1409810官方需求后的有符号余额，不是名为balance或deficit的字段。balance绑定14076d0资源残差。列车总库存83、未占用可用/余额+68，承诺15不是缺口。五个已证短缺类型的非负短少数与demanded一致，但缺口字段本身不升格，因官方没有独立的非负缺口量名称。28项新离线测试一次通过，Windows0。清单仍81/35，14表116字段3列，SHAb62c8bb5cd37404b28060a0820e6e7466283d4cb0f1a9cb1c535a045542479dc。未改生产或门、未capture/cloud。下一步world.own_units.supply.isolated或equipment.affected_plan_ids。

## t222 独立隔绝提示消费者
HQ_WITHDRAWAL_BLOCKED_ENCIRCLED的两个原生消费者通过C47C40反转E64C50；该连通谓词不等于consumer1E/Army2E字节或补给率。新RTTI确认省份+D0是CControllerArea，撤回原始记录临时landmass命名；EEF530是GS698成员查询而非海域分类。49个己方对象中46个51身份支持、3个4713仍拒绝；30走标志捷径，16个标志0仍由首都控制区分支判定连通，隔绝正例0，isolated不升格。30个新离线测试方法/27个非重叠语义组通过，Windows0；清单仍81/35、14表116字段3列，SHAb62c8bb5cd37404b28060a0820e6e7466283d4cb0f1a9cb1c535a045542479dc。保留t221原生签名余额与派生非负shortfall的区别，deficit不升格。下一步equipment.affected_plan_ids官方因果消费者，不重复空计划采样。

## t223 因果计划候选与实际渲染证据
低装备警报实际访问CDeploymentStatus+78活动请求，不是COrderInstance，不能代证affected_plan_ids；己方空计划数组读取0次。转向具体可见性链：16B2EB0生成原生渲染字节，131C770/134AE00门150，170BDA0富显示门250；陆军tier0/1/2/3映射0/150/250/250后结合省overlay与modifier24B，不能归一化为confidence。实际己方3场战斗中8个51身份对象：5字节255、3字节250，1个4652/type4713仍拒绝。全部observer表空但overlay非空，不能由空表推定不可见。Fog1经静态控制台ON/OFF路径独立绑定，未调用控制台。24B在79项有序列表中不存在；补齐owner443重映射368而非3后才能认定字节250。仍缺visible_units/spotted精确语义和原生阴性对照，均不升格。28唯一测试方法通过，其中25新任务语义场景+3通用完整性场景；2轮共55次调用不冒充55独立测试。清单仍81/35、14表116字段3列，SHAb62c8bb5cd37404b28060a0820e6e7466283d4cb0f1a9cb1c535a045542479dc。下步继续独立counter/selection消费者语义，不重复空计划或observer采样；保留ControllerArea/registry和原生余额/派生缺口区别。

## t224 官方揭示门与原生阴性对照
134AE00在原生字节门150后使用INTEL_DIVISION_REVEALED，独立渲染队列131C770同门150；170BDA0的250实际是deployed_general_base_plate，不是通用spotted阈值。已知参战对手443最多64候选，只查2个即获得399原生250阳性、481原生0阴性；后者由CWarRelation+49=0的共享否分支、空observer头和overlay0独立闭合，雾ON、24B缺省0、重映射443->368不等于3。限定普通陆军51/kind0、已知对手、普通陆省、上述门及原生0/250/255分支，升格visible_units过滤能力和spotted；未观察的中间字节分支仍拒绝，并不将语义阈值改成250。不是完整可见列表/Input，relation/confidence仍未验证，不把渲染字节归一化为置信度。26唯一方法通过：17任务场景+9共享门/完整性/保留场景，一轮26调用，Windows0。清单83/33，14表116字段3列，SHAebd57b52a517d88e51e39b10f3c3b529e2ce2b542e9fde5ebd9f9d2cb1871ae5。下步relation_to_player官方敌我语义消费者与敌友对照；保持所有生产门和只读边界。


## t225 — 独立外交谓词证据，暂不升级关系字段
已用官方 TRIGGER_HAS_WAR_WITH 工具提示及同一虚表求值器证明3↔443实际交战，并以3↔1、3↔16及self作非交战对照；非交战绝不推定盟友。玩家阵营指针为null，无真实友方关系正例，relation_to_player不升级，仍83/33、14表116字段3列。24个唯一离线测试一次通过（20专项+4共用保护），无Windows复放或旧套件重跑。生产四哈希、51与指纹门不变，游戏零写入/调用/推进。详见 records/t225_checkpoint.md、t225_diplomacy_semantic_proof.json。下一候选为独立命名的国家级当前补员人力needed消费者，不把师级missing求和冒充原生国家字段。


## t226 — 国家人力needed未冒用，转入原生补给警报
独立命名MANPOWER_USAGE与师级补员配送门均非已证国家补员需求，首8/49师满额且missing0不代表全国needed0，未升级字段。另证补给警报注册ID3/4、具名缓存阈值50000/20000与16D8D50原生有符号分桶；尚未证明对象输入和实际警报正例，不映射schema危机严重度。23个唯一离线场景一次通过（18专项+5共用），0Windows复放，仍83/33、14表116字段3列。生产四哈希及51/指纹门不变，游戏零写入/调用/推进。详见records/t226_checkpoint.md；下一目标B58150的B5825A/B585CA消费者数据流与真实正负例，不重扫已闭合入口。


## t227 — 海空基地警报与陆军补给因果见证
B58150实际映射海空基地警报5/6而非陆军3/4。独立B79D00链及当前CTheaterGroup缓存警报4，与479师缺补给阳性/374师阴性形成双重证据；仅升格crises.kind/unit_ids/province_ids三个窄见证字段，kind明确为组合schema注解而非原生Crisis枚举，不输出severity/notes或完整危机/Input。只查3/25成员，500中间对照不作bucket0见证。32唯一离线方法（27专项范围+5共享），两轮64调用，首轮10错误来自研究断言B79E64误写，按真实B79E65修正后末轮32全过；0Windows复放。清单86/30（18内存+12非内存未证），14表116字段3列，SHA8c51a0318d5d72dc3b0d2a67325462c16c42629abffddb1438f18b774e636740。生产51/指纹门及四哈希不变，游戏零写入/调用/推进。详见records/t227_checkpoint.md/t227_final_seal.json。下一目标已缓存alert4文本的crises.notes独立消费者；键/占位符不算notes，不推断严重度。


## t228 — 已缓存原文说明与独立范围一致性
B61660独立_delayed注册/存储、B79D00具名补充文本写入及B52A30/B525A0复制链，证明当前同源战区组警报4的672字节已缓存中文补充原文；非53字节模板或22字节标题，未调用格式化/本地化函数或替换键和占位符。仅升格crises.notes；原换行和0x11格式码保留。范围复核仅重绑原3/25成员，479因果见证、374健康阴性与500中间对照均不变；说明是战区组通用建议，不是每师诊断，海路建议仍为条件句。kind仍为组合注解，非原生枚举，无severity/完整危机记录/feed/Input。30唯一方法（25专项范围+5共享）通过；2次启动但首次导入依赖失败执行0测试，只有1轮完整套件/30调用，Windows0、旧套件0。清单87/29（17内存+12非内存未证），14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3。生产51/指纹门及四哈希不变，游戏零写入/调用/推进。详见records/t228_checkpoint.md/t228_final_seal.json。下一候选combats.result的独立胜负消费者与精确历史战斗编号连接，不重做已闭合日期换算。


## t229 — 原生历史胜负已证，活动编号连接仍不升格
独立具名win(E3)、defensive_victory3756与精确logger证明groupwin=selector XOR defensive_victory。14唯一历史引用（初始2条包含其中），13胜/1负；212与5为真实正负对照，214与5同selector但相反胜负。selector不是result；247为池槽数非战斗普查。活动type62/3072、3096、3097没有精确历史ID连接，故0升格。共同战争具名触发器与盟国scope为不同静态转向，无新外国友军样本、不再重采nullfaction。3个短factory槽及leaf后的邻居literal误归属均拒绝并保留原始源码审计ZIP。30唯一测试/2轮60调用；首轮15失败11错误因checker误拒精确序列化尾跳，修正后全30通过，Windows0旧套件0。清单保持87/29（17内存12非内存），14表116字段3列及SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3；生产51/指纹门/四哈希不变，游戏写入调用推进UI变化均0。危机3/25见证、组级缓存说明与非完整feed边界不变。详见records/t229_checkpoint.md及t229_final_seal.json。下一候选missing_divisions独立具名前线缺编消费者，需真实己方前线与正负样本，不以期望兵力或单位汇总替代。


## t230 — 己方战线成员已证，missing_divisions不升格
独立具名_TotalFrontDesiredNrDivisions是期望兵力，不是缺编。REQ_DIVS与garrison_order_headline/GARRISON_ORDER_CONF同窗，属驻防命令所需师标签，且因间接跳转0x177d3fa保持PARTIAL；所需不是缺口。官方国家theatre数组仅1项，其+0x50上5个CFront（1278、76、70、1734、1735）的+0x18均回指该theatre，为当前己方战线成员。相邻stride 0x1e0的CTheatre+0x50（3/73/3/8）不是己方成员。无具名缺编消费者，不以期望、驻防所需或所需减现有作为官方字段。30唯一测试/2次启动；首次导入因非ASCII字节字面量失败执行0测试，修正后30/30通过，总调用30，Windows0旧套件0。清单保持87/29（17内存12非内存），14表116字段3列及SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3；生产51/指纹门/四哈希不变，游戏写入调用推进UI变化均0。详见records/t230_checkpoint.md及t230_final_seal.json。下一候选crises.severity，须在既有警报/危机见证上找独立具名严重度消费者，不以警报3/4或阈值名称推断，不扩大3/25或notes/feed范围。


## t231 — 用户下机要求：立即保存研究检查点并停止
严重度研究未完成，0升格/0语义测试；6次研究启动5份JSON、1次断言失败，不算测试。+448同值5不能推严重度；ALERT_PRIORITY接收者与既有陆军危机连接未证。slot1 RVA误抄（应1eefb08、实际用了1eafb08）两次尝试均拒绝。原始资料和更正保留。清单87/29（17内存12非内存），14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。停止后仅文档保存同步，不再读取进程，不访问游戏存档；无后台任务，不自动恢复，须用户明确继续。详见records/t231_checkpoint_STOPPED.md、t231_stop_status.json。


## t232 — 明确继续后绑定重启会话，严重度域隔离
pt207u恢复授权。实际PID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，两门关闭，版本/生产四哈希/原生指纹一致；未复用旧10288堆址。修正真实第二槽1EEFB08为CNavyTheaterGroupItem副接口adjustor，确认navy UI priority而非陆军危机。新增alert_level解析器145E1C0属于COccupationModifier，当前原生token表独立证low/medium/high->配置+C8=0/1/2，非watch/high/critical，解析器整体仍PARTIAL。只重绑既有3/25见证，active4同组存在；0新成员/0notes原文读取/0严重度样本/0升格。24唯一测试一次收集一次运行24通过；研究collector另有1次无pdata断言失败，原源码保留，不算测试。另转front_invalidated具名字典检查F6A071入口，日志/loader错误不是战争导致失效证据。清单87/29（17内存12非内存），14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。生产51/门/四哈希不变，游戏写入/Post/原生调用/存档/推进/UI变化全0。详见records/t232_checkpoint.md、t232_final_seal.json。


## t233 — 当前前线字典、构造断言与具名controller变更链
实际PID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，逐块freshguard。F6A071是F69F30构造/更新的无效key断言，非战争失效布尔量。当前己方1theatre/5front，字典5值精确匹配；3直接key、2enemy key均有效，后两first-controller不同于保留front+70，不得误判失效。具名EndBundle Conquer/Relation与NotifyControllerChanged调用链已证，但controller变化不是外交战争因果，空scope不算schema false。7D有省份成员插入共享写入，不升格。20唯一离线测试1次运行20通过；研究6启动4成功2失败源码保留；最终59原生窗口重验。清单87/29（17内存12非内存），14表116字段3列与SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变；生产51/门/指纹/四哈希未改，游戏写入/Post/调用/存档/推进/UI全0。详见records/t233_checkpoint.md、t233_final_seal.json。


## t234 — 33EB090外交入队是共享flush，不是战争失效字段
实际PID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，逐块freshguard。F7BB20/F7BCE0/F7E1C0的LEA均入33EB090；NotifyControllerChanged仍为33EB020。独立具名DIPLOMACY_JOINED_WAR_*与pWarRelation消费者118DEF0以xor ecx,ecx调用F7E1C0，不是把交战双方作为显式参数入队。撤销保证、和平会议、事件、派系清理、志愿军与删除战区共享同一scope，故非wars.front_invalidated。D56B10复制全局pending表33EA908，当前count0/data空，不作为schema假值。748490/DA37F0无独立命名，不能当作at-war或己方前线桥。NNavy INTEL_LEVEL定义不是visibility.confidence。17唯一离线测试1次运行17通过；研究3启动全成功。清单87/29（17内存12非内存），14表116字段3列与SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变；生产51/门/指纹/四哈希未改，游戏写入/Post/调用/存档/推进/UI全0。详见records/t234_checkpoint.md、t234_final_seal.json。


## t235 — 国家陆军情报不是可见师置信度
PID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105逐块freshguard，106原生窗口终验。三NIntel模板计数getter只返回名字；CURRENT_ARMY_INTEL具名消费者以国家tag/kind1调用14CB760，army_intel表达式独立说明country domain，非师confidence。ASCII confidence0只为有界字符串发现，不是全局不存在证明。frontage_full(token338F)具名front-full入口与descriptor factory493900已证，但不是缺人导致战略战线守不住；不推导字段。0升格/0置信度样本/0新外军或observer读取。17唯一离线测试1次17通过，研究4启动全成功。清单87/29(17内存12非内存)、14表116字段3列与SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变；生产51/门/四哈希/指纹未改，游戏写入/Post/调用/存档/推进/UI全0。详见records/t235_checkpoint.md及final_seal。


## t237 recovery — t236 pending copies resolved
2026-11-21 EST: restored26 records (24pending +2helperJSONs), preserving prior BOX_PENDING_C audit byte-for-byte. Inventory87/29 SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3 unchanged. No new game access or terminal recheck claimed by this recovery; see records/t237_reconcile_receipt.json.


## t237 research — 计划无师警报仅聚合组键，非逐计划status
恢复t23624pending+2helperJSON且保留原pending审计，C与box SHA对齐。freshPID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，135旧+7新=142原生窗口终验。具名alert_battleplans_with_no_divs29C3DD0→ID43→B6F730→B5BB40独立插入/删除与递归链；当前缓存43为空仅是缓存缺席，不是逐计划阴性或全部可执行。0plan实例/0empty-plan轮询/0升格。17唯一离线方法1轮17通过；研究4执行3成功1失败（错误假定manager有RTTI，失败源码保留），guard/recovery/finalseal另计。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。生产51/四哈希/指纹门不变，游戏写/Post/调用/存档/推进/UI全0。下一步仅独立判明B620C0/B6DD96是聚合UI优先级还是逐项severity，不从颜色/448推导schema。详见records/t237_checkpoint.md及final_seal。


## t238 — B620C0仅静态警报ID分区，非severity；转独立教程计划方法
freshPID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，142旧+12新=154窗口终验，生产51/四哈希/门不变。B620C0忽略传入RCX，仅EDX经74项LUT返回AL0/1，已独立解析两个常量return分支；不是聚合优先级或逐项severity，已限定alert4也不进此UI分支。无颜色/448/阈值映射。新frontline/offensive_order精确教程构造器及RTTI/slot9方法→1A57380/1A57590入口，非原始plan类型；slot9调度/返回语义及真实计划关联未证，不能将type2/单元attackArrow当轴线。0plan/empty-plan/新crisis成员/notes/alert43缓存读取，0升格。20唯一离线方法(17专项3共享)1轮20通过；研究6执行全成功，guard/离线生成/finalseal另计。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无生产编辑/提交。下一步独立绑定两helper输出/国家句柄/真实COrderInstance成员及类型。详见records/t238_checkpoint.md及final_seal。


## t239 — 教程回调非只读getter；offensive匹配旧vertex非axis，转属国关系消费者
freshPID31576/base0x7ff72fc80000/SOV3/pause1/speed0/tick60781105，154旧+10新=164窗口终验；生产51/四哈希/门不变。1A57380/1A57590实际会写教程+50并传tutorial_objective_done给不透明虚调用，未调用且不能当只读bool。country引用经C07BF0/C08790/+340重映射到+310国家表，现场3→3→SOV；C085F0只比规范化索引非外交。frontline含type2+A8+ETH额外条件，不能type2命名。10B9240递归子计划+70匹配并收集指针，独立现有reader哈希证明+70已是vertex，非axis。新TRIGGER_IS_PUPPET441970/IS_SUBJECT442B60具名入口仅tooltip，下一步须独立触发器求值器和相对玩家overlord身份、可见部队owner桥，非任意属国/非战友好。0新字段真实样本/0plan或派系扫描/0升格。20唯一离线方法(17专项3共享)1轮全过；研究4执行全成功，guard/离线摘录/finalseal另计。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无生产编辑/提交。详见records/t239_checkpoint.md及final_seal。


## t240 — 精确属国方向消费者已绑定，现场负例不冒充可见关系
441970/442B60真实slot22求值器3F9EE0/3FA2E0是unary；新具名PUPPET_OF441690/ SUBJECT_OF442880经3F9E40/3FA270绑定source/target方向与+188亲属国引用、按target索引关系表、D87160消费token30D1现场精确名puppet。二元slot23=1443990动态目标表达式返回输出缓冲，非固定字段。前两次RTTI空发现因TD错误限.rdata，独立CTutFrontline的.data控制纠正；不是不存在证据。fresh同session31576/SOV3/pause1/speed0/tick60781105；当前combat3072/unit399的owner368→368=D04，不沿用旧443/CHI；+188=0且对player3关系+288空，只有负例，未重新验证visibility，无友好/中立/全feed或字段升格。164旧+8新=172窗口终验；生产51/四hash/门不变。20唯一离线方法17专项3共享，一轮20调用全过；研究6执行6成0异常，其中2空发现miss，guard和seal各1另计。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无后台、生产改动或commit。下一步定向国家引用查找取得真实属国正例，非census；升格仍需当前可见owner桥。详见records/t240_checkpoint.md及final_seal。


## t241 — 定向国家查找与真实属国方向正反例，仍不冒充玩家可见关系
763E10是FNV1a32字符串查找，763EA0是有界countryref数组访问；1D5170精确bucket.last逆链到first，未调用。根33DF288由native ETH消费者RIP推导。首次bucket收集误当polymorphic触发RTTI断言，失败原稿/记录保留；修正plainlayout不作类名声明。仅4定向lookup共4key：MAN113/JAP48/SOV3正确映射，QZQ桶有RHD但不相等故miss，非census。真实MAN→JAP父引用48+puppetflag1且dependency30D1双方48为正；JAP→MAN同样存在30D1记录但48≠113且无父/level为负，证明方向不能从记录存在/类型推出。两bool明确是native输入离线投影，非原始schema字段；JAP不是玩家SOV3，无新visibility或可见owner桥，0升格。175窗口=172旧+3新终验，生产51/四hash/门不变。20唯一方法17专项3共享1轮20调用全过；研究4执行3成功1RTTI断言失败，guard/seal各1另计，0spawn失败。清单87/29(17memory12nonmemory)，14表116字段3列，SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无后台或生产改动。下步具名allied/friendly消费者与定向真实对照，非nullfaction/nonwar推理。详见records/t241_checkpoint.md及final_seal。


## t242 — 具名faction双边无正例后转隔绝字段，拒绝错误+2E写者
43EB90具名IN_FACTION_WITH通过完整表280F220绑定3F90F0，双方country+F88/+2D8必须非空且相等；现场仅3定向国家SOV3/MON69/JAP48，SOV和MON均空，JAP非空，4方向2无序对全false，无历史友好/空相等推理，不再轮询。转独立isolated字段：29D6F78实际CArmy次级表COLoffset16，虚10/20是CED2E0持久化和CE95A0加载/token分派，未执行或访问存档。原间接跳转证据保留，离线精确解75索引7目标至653指令无剩余直接未解边；callee仍不透明。CE9A6B的+2E写者实际新48字节字符串，47字节常量Army refers to a non existing division template，非consumer/Army flag。0unit/visibility样本、0升格。180窗口=175旧+4code+1literal终验，生产51四hash门不变。20唯一方法17专项3共享1轮全过；研究4执行全成0fail；离线生成2启1成(缺capstone)，包安装2试1拒1隔离venv成功，均非测试/研究启动失败。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/调用/存档/推进/UI全0，无后台/生产改动。下步C58600次级receiver默认解析支路，须独立语义，不把loader当运行时隔绝。详见records/t242_checkpoint.md及final_seal。


## t243 — STOPPED：按用户t209u完成本步后保存停工
C58600完整4950字节/1103指令确认token/加载域，secondary receiver与别名须区分，无运行时isolated证明，未执行或访问存档。停工指示到达前已转不同字段combats.result，唯一可达1349260→1349680→D3B6D0显示side+28/+30及observer+1D0结构，但active/history ID桥仍未证明，0live样本/0升格，不重推win/date。12唯一离线方法9专项3共享，一轮12调用全过；研究2执行全成，guard/seal各1另计，0失败。182窗口=180旧+2新终验，生产51四hash门不变。清单87/29(17memory12nonmemory)、14表116字段3列、SHA8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3不变。游戏写/Post/native调用/存档/推进/UI全0。此为研究文档保存，非游戏存档。终验后停止所有研究与进程读取，无后台，无自动继续或t244；须用户明确继续。详见records/t243_checkpoint_STOPPED.md及final_seal。
