import sys,json,struct,hashlib
from pathlib import Path
R=Path(r'C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win');sys.path.insert(0,str(R/'calling'))
p=R/'calling/input_loaded_fields.py';s=p.read_text(encoding='utf-8');a=s.index('def own_plans(');b=s.index('\ndef province_land_neighbors',a)
new='''def own_plans(r, country):
    """Own COrderInstance objects across root/front/fallback lists; t198 official path contrast."""
    plans = []
    ev = {'instance_count': 0}
    seen = set()
    for tp in r.array(country + 0x168, 64):
        r.require(tp, 'CTheatre')
        for gp in r.array(tp + 0x80, 256):
            r.require(gp, 'COrdersGroup')
            army_id = r.i(gp + 0xc)
            for list_off in (0x98, 0xb0, 0xc8):
                for ip in r.array(gp + list_off, 256):
                    if ip in seen:
                        continue
                    seen.add(ip)
                    r.require(ip, 'COrderInstance')
                    ev['instance_count'] += 1
                    unit_ids = []
                    for mp in r.array(ip + 0x210, 256):
                        primary = mp - ORDERS_GROUP_MEMBER_THISADJ
                        r.require(primary, 'CArmy')
                        unit_ids.append(r.i(primary + 0x1c))
                    data, cap, n = struct.unpack('<QII', r.exact(ip + 0x70, 16))
                    if not 0 <= n <= cap <= 65536 or (n and data < 0x10000):
                        raise ObservationError('invalid plan path')
                    path = list(struct.unpack('<' + 'I' * n, r.exact(data, n * 4))) if n else []
                    if any(not 1 <= v <= 65535 for v in path):
                        raise ObservationError('invalid plan vertex province')
                    item = {
                        'plan_id': r.i(ip + 0x244),
                        'assigned_army_ids': [army_id],
                        'assigned_unit_ids': unit_ids,
                        'executing': bool(r.exact(ip + 0x248, 1)[0]),
                        'vertex_province_ids': path,
                    }
                    # type / axis / status omitted: no official named mapping or nonempty contrast yet
                    plans.append(item)
    return plans, ev


'''
p.write_text(s[:a]+new+s[b:],encoding='utf-8')
# append evidence metadata without invalidating historical evidence
p=R/'calling/tables/offsets_input_windows_1.19.5.json';d=json.loads(p.read_text(encoding='utf-8'));d['plan_vertex_t198']={'promoted':['world.plans.vertex_province_ids'],'path':'+0x70 token 0x174; COrderNewFallbackCommand -> 0x18d1150 -> 0x10b0d90','instance_lists':['+0x98','+0xb0','+0xc8'],'factory':'0x18d0330','vt':'0x2a85520','isvalid':'0x18df520','live_path':[2072,7944],'pid':12948};p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
inv=Path(r'D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md');s=inv.read_text(encoding='utf-8');lines=s.splitlines();matches=[i for i,ln in enumerate(lines) if ln.startswith('| world.plans.vertex_province_ids |')];assert len(matches)==1
lines[matches[0]]='| world.plans.vertex_province_ids | 已验证 | 官方 COrderInstance+0x70 path（token 0x174）；Fallback 命令后活体控制点为 [2072,7944]，须遍历集团军 +0x98/+0xB0/+0xC8 实例表。 |'
text='\n'.join(lines)+'\n';stage=Path(r'C:\Users\Lenovo\agent-tools\t198_inventory.md');stage.write_bytes(text.encode('utf-8'));print('STAGED',hashlib.sha256(stage.read_bytes()).hexdigest())
import py_compile
py_compile.compile(str(R/'calling/input_loaded_fields.py'),doraise=True)
# checkpoint chunk
(R/'research/t198_checkpoint.md').write_text('''# t198 checkpoint（逐块续写）
授权 pt183u。pid12948，ETH 1936-01-01 13:00，官方暂停，allow_post=false。

## 块1：官方路径
0x18d6660 = COrderInsertFrontCommand Execute，VT 0x2a852e0，factory0x18d01c0 size0x98，IsValid0x18df2a0。集团军411/实例2，front[2072,7944]、axis[7944,5097]、affected[2]、单位数组空，IsValid=1 后单次 Post，wait0/rax1。初次快照未见新实例，不靠空快照升格。
0x18d1150 是 COrderNewFallbackCommand Execute0x18d9030 的尾跳共享 helper，不是另一个独立工厂。已绑定 factory0x18d0330 size0x60，VT0x2a85520，IsValid0x18df520。集团军411、路径[2072,7944]、单位数组空，IsValid=1 后单次 Post，wait0/rax1；活体 +0xB0 实例6 和 +0xC8 实例5 的官方 +0x70=[2072,7944]，+0x258/+0x25c=0。两者均未执行。不能只看根列表+0x98。
升格 world.plans.vertex_province_ids；resolver 已加入三张实例数组、去重和官方路径。未动校验器/哨兵，未整段清零，未对师发 SetArmyLeader。下一块先关闭计划1执行并确认false，再做1x短对照。
''',encoding='utf-8')
