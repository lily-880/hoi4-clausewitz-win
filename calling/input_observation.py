"""Bounded, read-only division observations; NOT a complete GeneralissimoInput.

The caller provides a read(address, size) callback and *freshly resolved* context.
No process attachment, memory scanning, writes, or orders occur in this module.
Default layout is historical Windows 1.19.4 evidence; any supplied layout label
requires independent matching-version proof outside this module before calling. Optional/unproved fields are never defaulted.
"""
from __future__ import annotations
import struct

FIXED = 100000
MAX_DIVISIONS = 4096

class ObservationError(ValueError):
    pass

def _ptr(value):
    return type(value) is int and 0x10000 <= value < 0x7fffffffffff

def observe_own_divisions(read, country_ptr, player_index, *, carmy_vtable,
                          version_verified=False, limit=MAX_DIVISIONS,
                          layout_label="Windows HOI4 1.19.4",
                          strength420_semantics="unclassified"):
    """Return partial units + evidence; refuse unknown version or invalid lists.

    `version_verified` is an explicit caller gate, not automatic verification.
    Positive handle/province/owner/vtable checks are required for every row.
    The whole observation fails closed on an invalid row; no silent truncation.
    A supplied reader must raise on failed/short reads; we also enforce length.
    Names/templates, supply, current manpower, in_combat and orders are absent.
    strength420_semantics=current is required by the fingerprinted1.19.5 caller;
    the default unclassified mode emits no HP field and cannot claim max.
    """
    if version_verified is not True:
        raise ObservationError('version not verified against historical layout')
    if not _ptr(country_ptr) or not _ptr(carmy_vtable):
        raise ObservationError('invalid context pointers')
    if type(player_index) is not int or not 0 <= player_index < 10000:
        raise ObservationError('invalid player index')
    if type(limit) is not int or not 0 < limit <= MAX_DIVISIONS:
        raise ObservationError('invalid division bound')
    if strength420_semantics not in ("unclassified", "current"):
        raise ObservationError("unproved strength420 semantics")
    reads = 0
    def exact(address, count):
        nonlocal reads
        data = read(address, count)
        reads += 1
        if not isinstance(data, bytes) or len(data) != count:
            raise ObservationError('short read at %#x' % address)
        return data
    def unpack(fmt, data, at=0):
        return struct.unpack_from(fmt, data, at)[0]
    first = exact(country_ptr + 0x290, 16)
    data, capacity, size = struct.unpack('<QII', first)
    if size > capacity or size > limit or capacity > 100000:
        raise ObservationError('invalid/oversized country division array')
    if size and not _ptr(data):
        raise ObservationError('invalid division array data')
    pointers = exact(data, size * 8) if size else b''
    units, evidence, seen, seen_ptrs = [], [], set(), set()
    for slot in range(size):
        ap = unpack('<Q', pointers, slot * 8)
        if not _ptr(ap) or ap in seen_ptrs:
            raise ObservationError('null/duplicate division pointer at slot %d' % slot)
        seen_ptrs.add(ap)
        # Bounded object prefix, no heap scan and no dereference of arbitrary fields.
        blob = exact(ap, 0x56c)
        vt = unpack('<Q', blob)
        handle_type, uid = struct.unpack_from('<II', blob, 0x18)
        owner = unpack('<i', blob, 0x1e0)
        province = unpack('<I', blob, 0x28)
        province_ptr = unpack('<Q', blob, 0x1f0)
        if vt != carmy_vtable or handle_type != 0x33 or owner != player_index:
            raise ObservationError('division class/handle/owner mismatch at slot %d' % slot)
        if uid == 0 or uid in seen or province == 0 or not _ptr(province_ptr):
            raise ObservationError('invalid unit/province reference at slot %d' % slot)
        seen.add(uid)
        if unpack('<I', exact(province_ptr + 0xa4, 4)) != province:
            raise ObservationError('province cross-check mismatch at slot %d' % slot)
        # Unclassified historical evidence is diagnostic only, NEVER maxHP.
        # 1.19.5 explicitly selects CURRENT after t167 dataflow proof.
        strength420 = unpack('<q' if strength420_semantics == 'current' else '<i', blob, 0x420) / FIXED
        org = unpack('<q' if strength420_semantics == 'current' else '<i', blob, 0x428) / FIXED
        equipment = unpack('<q' if strength420_semantics == 'current' else '<i', blob, 0x468) / FIXED
        if not (0 <= strength420 <= 100000 and 0 <= org <= 100000 and 0 <= equipment <= 1):
            raise ObservationError('invalid fixed-point scalars at slot %d' % slot)
        row = {'unit_id': uid, 'province_id': province,
               'owner': {'index': owner}, 'relation_to_player': 'self',
               'organization': org,
               'strength': {'equipment_ratio': equipment}}
        if strength420_semantics == 'current':
            row['strength']['current'] = strength420
        leader = unpack('<i', blob, 0x564)
        if leader >= 0:
            row['leader_id'] = leader
        elif leader != -1:
            raise ObservationError('invalid leader ID at slot %d' % slot)
        units.append(row)
        evidence.append({'unit_id': uid, 'slot': slot,
                         'strength420_unclassified' if strength420_semantics == 'unclassified' else 'strength420_current': strength420,
                         'unresolved_manpower_4f0': unpack('<i', blob, 0x4f0) / FIXED})
    # Recheck array header AND membership to reject list edits during the read.
    if exact(country_ptr + 0x290, 16) != first:
        raise ObservationError('division array changed during observation')
    if size and exact(data, size * 8) != pointers:
        raise ObservationError('division membership changed during observation')
    return {'world': {'own_units': units}, '_observation': {
        'complete_input': False, 'historical_layout': layout_label,
        'version_gate': 'caller_supplied', 'read_calls': reads,
        'consistency': 'list-stable only; scalar values are not atomic',
        'unproven_required_unit_fields': ['in_combat', 'order'],
        'evidence': evidence}}

def unit_blockers(unit):
    """Necessary Unit shape checks only, never a full-schema compliance claim."""
    errors = []
    for key in ('unit_id', 'province_id', 'owner', 'relation_to_player', 'in_combat', 'order'):
        if key not in unit:
            errors.append(key + ': missing required field')
    if 'in_combat' in unit and type(unit['in_combat']) is not bool:
        errors.append('in_combat: expected bool')
    if 'template' in unit and 'template_id' not in unit['template']:
        errors.append('template.template_id: missing required field')
    order = unit.get('order')
    if order is not None:
        if not isinstance(order, dict):
            errors.append('order: expected object')
        else:
            for key in ('type', 'target_province_ids', 'path_province_ids'):
                if key not in order:
                    errors.append('order.' + key + ': missing required field')
            if order.get('type') not in ('idle', 'move', 'strategic_redeploy', 'attack',
                'support_attack', 'retreat', 'garrison', 'training', 'exercise', 'unknown'):
                errors.append('order.type: invalid enum')
            for key in ('target_province_ids', 'path_province_ids'):
                if key in order and (not isinstance(order[key], list) or any(type(x) is not int for x in order[key])):
                    errors.append('order.' + key + ': expected int[]')
    return errors
