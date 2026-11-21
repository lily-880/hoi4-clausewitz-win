"""Offline replay of this Windows build's captured calendar instructions only.
Not production code, a CLI, game accessor, epoch guess, or historical-ID bridge.
PositiveAD/signed32 scope, proof-gated; never imports a game/process backend.
"""
EPOCH=43800000
MONTHS=(31,28,31,30,31,30,31,31,30,31,30,31)
REQUIRED={
 'month':['17f7f0 mov edx, dword ptr [rcx + 8]','17f7f8 sub edx, 0x29c55c0','17f7f3 mov eax, 0x2aaaaaab','17f813 mov eax, 0xb38cf9b1','17f828 imul eax, edx, 0x16d','17f82e sub r9d, eax','17f831 sub r9d, dword ptr [rip + 0x2f7d9d8]'],
 'day':['17f46d call 0x17f7f0','17f53f sub ecx, 0x29c55c0','17f575 sub r8d, r9d','17f578 mov eax, r8d'],
 'formatter':['22d8365 call 0x17f7f0','22d836f call 0x17f460','22d8378 lea r9d, [rdi + 1]','22d8383 lea r11d, [rax + 1]','22d83ab sub r10d, eax','22d83b6 inc r10d','22d83bc mov dword ptr [rsp + 0x28], r10d','22d83c7 mov dword ptr [rsp + 0x20], r11d','22d83d3 lea rdx, [rip + 0x8de1ce]']}

def i32(x):
 return (x+2**31)%2**32-2**31

def hi32(a,b):
 return i32((i32(a)*i32(b))>>32)

def native_div24(n):
 q=hi32(n,0x2aaaaaab)>>2
 return q+((q&0xffffffff)>>31)

def native_div365(n):
 q=i32(hi32(n,0xb38cf9b1)+n)>>8
 return q+((q&0xffffffff)>>31)

def native_div8760(n):
 q=i32(hi32(n,0xef66a241)+n)>>13
 return q+((q&0xffffffff)>>31)

def _parts(raw):
 if type(raw)is not int or not EPOCH+8760<=raw<2**31:raise ValueError('outsidecapturedpositiveAD/signed32scope')
 n=raw-EPOCH;days=native_div24(n);year=native_div365(days)
 if year!=native_div8760(n):raise ValueError('independentnativeyeardividersdisagree')
 doy=days-year*365;left=doy;month=0
 while left>=MONTHS[month]:left-=MONTHS[month];month+=1
 return {'year':year,'month':month+1,'day':left+1,'hour':n-days*24+1},doy

def validate(proof):
 if proof['version']!='1.19.5.0.7c6c' or proof['date_class']!='.?AVCGameDate@@':raise ValueError('unsupportedbuild/type')
 if proof['epoch_hours']!=EPOCH or proof['year_days']!=365 or tuple(proof['month_lengths'])!=MONTHS:raise ValueError('unprovedcalendarconstants')
 if proof['format_literal']!='%04d.%02d.%02d.%02d' or proof['format_rva']!='0x2bb65a8':raise ValueError('unprovednativeformat')
 if proof['guard']!=proof['after']:raise ValueError('changedsession')
 g=proof['guard']
 if g['pause']!=1 or g['speed_slot']!=0 or g['markers']!={'safe_land_tool_gate.OPEN':False,'strategic_only_tool_gate.OPEN':False}:raise ValueError('guardnotclosed')
 for key,anchors in REQUIRED.items():
  f=proof['flows'][key]
  if f['unresolved_edges'] or any(a not in f['asm']for a in anchors):raise ValueError('incompletenativeproof')
 gt,doy=_parts(proof['raw_hours_signed32'])
 if gt!=proof['GameTime']or(gt['year'],doy,gt['hour'])!=(g['year'],g['day_index'],g['ui_hour']):raise ValueError('independentcachedcontrolfailed')
 if proof['excluded_mutator']['never_invoked']is not True:raise ValueError('mutatornotexcluded')
 return True

def replay(raw,proof):
 validate(proof)
 return _parts(raw)[0]

def native_text(raw,proof):
 x=replay(raw,proof)
 return proof['format_literal']%tuple(x[k]for k in ['year','month','day','hour'])

def month_partition(raw,proof):
 x=replay(raw,proof)
 return 12*x['year']+x['month']-1
