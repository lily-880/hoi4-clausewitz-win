from _t202_common import *
# Local research corrections and durable block, no production reader edits.
def load(n):return json.loads((R/'research'/n).read_text(encoding='utf-8'))
def save(n,d):(R/'research'/n).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
d=load('t202_deep_semantics.json')
for row in d['plan_geometry_inputs']:row['orders_group_ptr38']=row.pop('parent_ptr38',row.get('orders_group_ptr38'))
d['geometry_note']='COrderInstance+38 is live RTTI COrdersGroup, not parent instance. Parent links are +1e0 and reciprocal child lists. Empty +280 is not an axis proof.';save('t202_deep_semantics.json',d)
d=load('t202_renderer_loss_bridge.json')
for row in d['plan_group_binding']:row['group_raw_u32_8']=row.pop('orders_group_id8',row.get('group_raw_u32_8'))
d['group_note']='u32(+8)=53 is raw only, not claimed group ID; group IDs are not inferred from this field.';save('t202_renderer_loss_bridge.json',d)
d=load('t202_native_stat_axis.json');d['semantic_correction']='+140 entries have CAirInLandCombat vtable; +130 is live CCombatTactic. Neither is a manpower casualty record. record_strings were rejected raw-object-as-text attempts and have no semantic standing.';save('t202_native_stat_axis.json',d)
d=load('t202_isolated_binding.json');d['rejected_unbound_slot_candidate']=d.pop('primary_changer_predicate',d.get('rejected_unbound_slot_candidate'));d['rejection_note']='CTemplateChanger vtable has six slots in current RTTI walk; +218 is beyond that table and NOT its predicate. It was never called. E64C50 has confirmed CArmy consumer but text says cannot process delivery (possibly cut off), not exact isolation.';save('t202_isolated_binding.json',d)
p=R/'research/_t202_deep.py';p.write_text(p.read_text(encoding='utf-8').replace("'parent_ptr38'","'orders_group_ptr38'"),encoding='utf-8')
p=R/'research/_t202_bridge.py';p.write_text(p.read_text(encoding='utf-8').replace("'orders_group_id8'","'group_raw_u32_8'"),encoding='utf-8')
d=load('t201_promotions_pending_inventory.json');d['t202_new_promotions']=[];d['t202_note']='No new schema field promoted. All pending t201 status changes remain unapplied; no D access.';save('t202_promotions_pending_inventory.json',d)
with(R/'research/t202_checkpoint.md').open('a',encoding='utf-8')as f:f.write("""
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
""")
print('BLOCK3_SAVED',hashlib.sha256((R/'research/t202_checkpoint.md').read_bytes()).hexdigest())
