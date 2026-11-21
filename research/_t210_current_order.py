"""t210 session-specific strategic redeployment proof only; never production capture.
Native CUnitStrategicMoveAction -> CEBF90(Army+2AF), C570E0 getter,
19F5590 independently names strategic redeployment. Other states omitted.
"""
from input_observation import ObservationError
from _t208_order_target import movement_destination

def current_strategic_order(r, gs, country, army):
    r.require(country, 'CCountry'); r.require(army, 'CArmy')
    if army not in r.array(country + 0x290, 4096):
        raise ObservationError('not in player country unit array')
    if r.i(army + 0x18) != 51 or r.i(army + 0x1c) <= 0:
        raise ObservationError('unproved own unit handle')
    flag = r.exact(army + 0x2af, 1)[0]
    if flag not in (0, 1):
        raise ObservationError('invalid native strategic flag')
    if flag == 0:
        return None
    if r.i(army + 8) != 0:
        raise ObservationError('unproved movement kind')
    if r.array(army + 0x1a8, 128):
        raise ObservationError('active combat branch not classified')
    if r.q(army + 0x1e8) or r.q(army + 0x2f8):
        raise ObservationError('support or transport branch not classified')
    if any(r.exact(army + off, 1)[0] != 0 for off in (0x24c, 0x24d, 0x2ae)):
        raise ObservationError('retreat withdraw or exile branch not classified')
    dst = movement_destination(r, gs, country, army)
    if dst is None:
        return None
    return {'unit_id': dst['unit_id'], 'order': {'type': 'strategic_redeploy'}}
