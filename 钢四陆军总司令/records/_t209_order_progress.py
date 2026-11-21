"""t209 Windows-session-specific current-edge progress proof; NOT production capture.
Native C52C90/C51970 -> C52FD0 -> C52BE0/14A6290.
16E60C5/16E61AB consume the fixed result divided by native float100000.
Only the already-qualified unqueued own-route branch is supported.
No ETA hours, entire-route completion, inferred order.type or native invocation.
"""
import struct
from input_observation import ObservationError
from _t208_order_target import movement_destination, _header

def current_edge_progress(r, gs, country, army):
 dst = movement_destination(r, gs, country, army)
 if dst is None:
  return None
 if r.i(army + 8) != 0:
  raise ObservationError('unproved army movement-kind branch')
 path, _ = _header(r, army + 0x200)
 next_id = r.i(path)
 provinces = r.array(gs + 0x2b0, 131072)
 if not 1 <= next_id < len(provinces):
  raise ObservationError('next province outside official registry')
 current = r.q(army + 0x1f0)
 nxt = provinces[next_id]
 r.require(current, 'CProvince'); r.require(nxt, 'CProvince')
 current_id = r.i(current + 0xa4)
 if not 1 <= current_id < len(provinces) or provinces[current_id] != current:
  raise ObservationError('current province identity mismatch')
 if r.i(nxt + 0xa4) != next_id:
  raise ObservationError('next province identity mismatch')
 cg, ng = r.q(current + 0xb8), r.q(nxt + 0xb8)
 if cg < 0x10000 or ng < 0x10000:
  raise ObservationError('invalid province geometry pointer')
 if r.exact(cg + 0xd2, 1)[0] & 3 != 1 or r.exact(ng + 0xd2, 1)[0] & 3 != 1:
  raise ObservationError('nonordinary-land distance branch not covered')
 data, cap, count = struct.unpack('<Qii', r.exact(cg + 0x70, 16))
 if not 0 <= count <= cap <= 4096 or (count and data < 0x10000):
  raise ObservationError('invalid bounded edge array')
 raw = r.exact(data, count * 48) if count else b''
 distances = [struct.unpack_from('<q', raw, j * 48 + 0x18)[0]
              for j in range(count) if struct.unpack_from('<i', raw, j * 48 + 8)[0] == next_id]
 if len(distances) != 1:
  raise ObservationError('missing or ambiguous current edge; native fallback not accepted')
 distance = distances[0]
 progress = struct.unpack('<q', r.exact(army + 0x240, 8))[0]
 if not 0 <= progress <= distance or distance <= 0 or progress > ((1 << 63) - 1) // 100000:
  raise ObservationError('invalid or overflow/sentinel movement progress')
 fixed = progress * 100000 // distance
 return {'unit_id': dst['unit_id'], 'eta': {'progress': fixed / 100000}}
