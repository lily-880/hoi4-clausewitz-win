exec(open(__file__.replace('_t200_semantic.py','_t200_start.py'),encoding='utf-8').read().split('# one opening')[0])
# typed RTTI inheritance, not a heap sweep
def rtti(vt):
 col=struct.unpack('<Q',p.read_rva(vt-8,8))[0]-0x140000000
 sig,off,cd,td,ch,selfr=struct.unpack('<6I',p.read_rva(col,24));h=struct.unpack('<4I',p.read_rva(ch,16));n=h[2];assert n<200
 rec={'vt':hex(vt),'col_offset':off,'bases':[]}
 for j in range(n):
  bd=struct.unpack('<I',p.read_rva(h[3]+4*j,4))[0];t,num,m,pp,v,attr=struct.unpack('<IIiiiI',p.read_rva(bd,24));name=p.read_rva(t+16,200).split(b'\0')[0].decode('ascii','replace');rec['bases'].append({'name':name,'mdisp':m,'pdisp':pp,'vdisp':v,'attributes':attr})
 return rec
profile=json.loads((R/'calling/tables/offsets_input_windows_1.19.5.json').read_text(encoding='utf-8'));vt=profile['vtable_rvas']['CArmy'];vt=int(vt,0)if isinstance(vt,str)else vt
hier={}
for name,v in(('CArmy',vt),('CLandCombat',0x2a237b8),('COrderInstance',0x2a026c0)):
 try:hier[name]=rtti(v)
 except Exception as e:hier[name]={'error':str(e)}
(R/'research/t200_rtti_hierarchies.json').write_text(json.dumps(hier,indent=2),encoding='utf-8');print('HIERARCHIES',json.dumps(hier,indent=2))
lines=(R/'research/_t200_clip_fc9880.txt').read_text(encoding='utf-8').splitlines();selected=[l for l in lines if 0xfca180<=int(l.split()[0],16)<=0xfca660];(R/'research/_t200_plan_type_tooltip_excerpt.txt').write_text('\n'.join(selected),encoding='utf-8');print('PLAN_TOOLTIP','\n'.join(selected))
# new lifecycle evidence only from historical files
failed=json.loads((R/'research/t198_order_sample.json').read_text());success=json.loads((R/'research/t198_pause_recovery.json').read_text());summary={k:failed[k]for k in('repause_prepared','unpause_prepared','posts','pause','exception')};summary['poll_count']=len(failed['polls']);summary['poll_clock_changed']=failed['polls'][0]['date']!=failed['polls'][-1]['date'];summary['success']=success;summary['missing_evidence']=['failed precreated object bytes immediately before Post','serialized bool/name payload at sink','drained clone pointer/bytes','Execute entry trace and actual time','state setter result/competing pause events'];summary['ruled_out_static']=['factory has no creation timestamp/sequence assignment: +1c/+20 initialized0','sink assigns sequence at Post, not factory','Clone explicitly copies +48/+49 flags and string+28','Post RAX1 means sink invoked; is not Execute status'];summary['proven_harness_bug']='unpaused=False is set after posting requested pause, before verifying official pause. Assertion fails after false assignment, so exception handler suppresses emergency branch. This is a confirmed containment bug, not proof of why the underlying command failed.'
(R/'research/t200_pause_history_diagnosis.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('PAUSE_HISTORY',json.dumps(summary,indent=2))
