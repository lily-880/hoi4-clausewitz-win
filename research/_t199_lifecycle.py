exec(open(__file__.replace('_t199_lifecycle.py','_t199_inspect.py'),encoding='utf-8').read().split('c=json.loads')[0])
pdata=next(s for s in p.sections if s.name=='.pdata');fns=list(struct.iter_unpack('<III',p.data[pdata.raw_ptr:pdata.raw_ptr+pdata.raw_size//12*12]))
for a in (0x147d480,0x147e8e0,0x1348e10,0x133e5d0,0x25473c0):
 fn=next(((s,e)for s,e,u in fns if s<=a<e),None);n=min(fn[1]-a if fn else 80,0x1000);lines=[f'{i.address:x} {i.mnemonic} {i.op_str}'for i in cs.disasm(p.read_rva(a,n),a)];(R/f'research/_t199_clip_{a:x}.txt').write_text('\n'.join(lines),encoding='utf-8');print('FN',hex(a),'\n'.join(lines))
