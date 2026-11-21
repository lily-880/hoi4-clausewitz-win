exec(open(__file__.replace('_t199_next.py','_t199_inspect.py'),encoding='utf-8').read().split('c=json.loads')[0])
schema=json.loads((R/'calling/tables/generalissimo_input.schema.json').read_text(encoding='utf-8'));print('META',json.dumps(schema['properties']['meta'],ensure_ascii=False))
s=(R/'calling/input_loaded_fields.py').read_text(encoding='utf-8');start=s.index('def own_armies(');end=s.index('def own_plans(',start);print('FORMATIONS',s[start:end])
# full combat tick routine, and primary virtual function heads
pdata=next(s for s in p.sections if s.name=='.pdata');fns=list(struct.iter_unpack('<III',p.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size//12*12]))
for a in (0x133e650,):
 fn=next(((s,e)for s,e,u in fns if s<=a<e));lines=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(p.read_rva(a,fn[1]-a),a)];(R/f'research/_t199_clip_{a:x}.txt').write_text('\n'.join(lines),encoding='utf-8');print('COMBAT_TICK','\n'.join(lines))
for j in range(20):
 a=struct.unpack('<Q',p.read_rva(0x2a237b8+8*j,8))[0]-0x140000000
 if 0<a<0x2700000:
  lines=[f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(p.read_rva(a,40),a)];print('VT',j,'\n'.join(lines[:8]))
