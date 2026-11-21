"""t208 process-specific research proof only. Not production capture/gate acceptance.
Native C528C0 -> GS+8 vf0(1E07F0) resolves Army.path.back.
195E950 uses that province as the current-route ETA destination; C52D20
separately uses path.front for current-edge progress subtraction.
Only observed own, +1E8-zero, unqueued current-route branch is accepted.
No process backend, execution, mutation, Post, saves, or path fallback.
"""
import struct
from input_observation import ObservationError

def _header(r,a):
 p,cap,n=struct.unpack('<QII',r.exact(a,16))
 if not 0<=n<=cap<=4096 or(n and p<0x10000):
  raise ObservationError('invalid bounded movement array')
 return p,n

def movement_destination(r,gs,country,army):
 r.require(country,'CCountry');r.require(army,'CArmy')
 if army not in r.array(country+0x290,4096):
  raise ObservationError('not in actual player country unit array')
 if r.i(army+0x18)!=51 or r.i(army+0x1c)<=0:
  raise ObservationError('unproved unit handle identity')
 if r.q(army+0x1e8):
  raise ObservationError('separate province-target branch not covered')
 if _header(r,army+0x220)[1] or _header(r,army+0x2c0)[1]:
  raise ObservationError('queued/full path branch not covered')
 p,n=_header(r,army+0x200)
 if not n:return None
 goal=r.i(p+(n-1)*4)
 provinces=r.array(gs+0x2b0,131072)
 if not 1<=goal<len(provinces):
  raise ObservationError('goal province outside official registry')
 province=provinces[goal];r.require(province,'CProvince')
 if r.i(province+0xa4)!=goal:
  raise ObservationError('goal province identity mismatch')
 return {'unit_id':r.i(army+0x1c),'target_province_ids':[goal]}
