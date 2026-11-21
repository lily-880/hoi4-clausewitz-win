"""Captured Windows-session research certificate only. No process/backend imports.
Not a production reader, generic resolver, CLI, or capture-gate replacement.
Only3096/3097, ordinary land sides, positive ground-org counters, air-org==0.
"""
import json
from pathlib import Path

REQUIRED = {
 'base_ctor': ['147c360 mov qword ptr [rcx + 0x18], rdx'],
 'side_ctor': ['133a21f xor ebp, ebp','133a27f mov qword ptr [rsi + 0x178], rbp','133a286 mov qword ptr [rsi + 0x180], rbp','133a294 mov qword ptr [rsi + 0x190], rbp'],
 'birth': ['133e5fd mov r8b, 1','133e600 mov rdx, rbx','133e606 call 0x133a1c0','133e60c mov qword ptr [rbx + 0x28], rax','133e624 xor r8d, r8d','133e627 mov rdx, rbx','133e62d call 0x133a1c0','133e633 mov qword ptr [rbx + 0x30], rax'],
 'writer': ['134d60d mov rbx, rcx','134d679 mov r8, qword ptr [rbx + 0x180]','134d685 mov edx, 0x374a','134d68d call 0x2545f90','134d647 mov r8, qword ptr [rbx + 0x170]','134d653 mov edx, 0x3537','134d6ab mov r8, qword ptr [rbx + 0x190]','134d6b7 mov edx, 0x3af5'],
 'ground_apply_caller': ['13436b5 call qword ptr [rax + 0x120]','1343725 call qword ptr [rax + 0xc0]','134375a call qword ptr [rax + 0x120]','1343760 mov r8, qword ptr [rsp + 0xb8]','134376b mov rax, qword ptr [rsp + 0xd0]','134377b sub rax, qword ptr [rcx]','1343794 add qword ptr [r8 + 0x180], rax'],
 'org_getter': ['ce4d60 mov rax, qword ptr [rcx + 0x428]','ce4d67 mov qword ptr [rdx], rax','ce4d6a mov rax, rdx','ce4d6d ret '],
 'army_apply': ['cec4b4 mov rcx, qword ptr [r15 + 0x428]','cec4c2 sub rcx, rdi','cec4d9 mov qword ptr [r15 + 0x428], rcx','cec4f1 mov qword ptr [r15 + 0x428], r8'],
 'air_apply_caller': ['133b1c7 call qword ptr [rax + 0x120]','133b1dd call qword ptr [rax + 0xc0]','133b206 call qword ptr [rax + 0x120]','133b20f mov rax, qword ptr [rbp - 0x59]','133b213 sub rax, qword ptr [rcx]','133b229 add qword ptr [rdx + 0x170], rax'],
}
EXPECTED_NAMES = {'0x374a':'ground_damage_org','0x3537':'air_damage_org','0x3af5':'prevented_damage_org','0x2ecb':'organisation','0x3750':'manpower_lost'}
MARKERS = {'safe_land_tool_gate.OPEN':False,'strategic_only_tool_gate.OPEN':False}

def _need(v):
 if not v: raise ValueError('unproven captured organization-loss input')

def _integer(v, minimum=0):
 _need(type(v) is int and minimum <= v < 2**63)
 return v

def certify(data, combat_id):
 """Return a narrow certificate, or None. No fake zero or manpower members."""
 try:
  _need(type(combat_id) is int and combat_id in (3096,3097))
  g=data['guard_before'];_need(g==data['guard_after'])
  _need((g['pid'],g['base'],g['country_index'],g['hour_tick'])==(6496,'0x7ff758fc0000',3,60781105))
  _need(g['pause']==1 and g['speed_slot']==0 and g['markers']==MARKERS)
  _need(data['tag']=='SOV' and data['version']=='1.19.5.0.7c6c' and data['own_plans']==[])
  _need(_integer(data['stable_dependencies'],1)>0)
  _need(data['production_capture_run'] is False and data['complete_input'] is False)
  _need(type(data['scale']['fixed']) is int and data['scale']['fixed']==100000)
  _need(data['scale']['input_observation_sha256']=='27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6')
  for token,name in EXPECTED_NAMES.items():_need(data['names'][token]==name)
  for key,insns in REQUIRED.items():
   f=data['native'][key];_need(f['unresolved_edges']==[])
   _need(all(s in f['asm'] for s in insns))
  selected=[c for c in data['combats'] if c['id']==combat_id];_need(len(selected)==1);c=selected[0]
  _need(c['handle_type']==62 and c['class']=='.?AVCLandCombat@@')
  _need(len(c['sides'])==2 and {s['side'] for s in c['sides']}=={'attacker','defender'})
  _need(len({s['ptr'] for s in c['sides']})==2)
  own=set(data['own_units']);_need(len(own)==len(data['own_units']) and own)
  casualties={};raws={};all_members=set()
  for s in c['sides']:
   _need(s['class']=='.?AVCLandCombatant@@' and s['vtable']=='0x2a236a0')
   _need(s['parent']==c['ptr'] and s['forward_offset']==('0x28' if s['side']=='attacker' else '0x30'))
   _need(s['members'])
   flags=[]
   for m in s['members']:
    _need(m['class']=='.?AVCArmy@@' and m['type']==51 and m['vtable']=='0x29d6d98')
    _integer(m['id'],1);_integer(m['logical_country'],1)
    _need(m['ptr'] not in all_members);all_members.add(m['ptr'])
    mine=m['ptr'] in own;_need(mine==(m['logical_country']==g['country_index']));flags.append(mine)
   _need(all(flags) or not any(flags));key='our_org_loss' if all(flags) else 'enemy_org_loss'
   _need(key not in casualties)
   # Nonzero air coverage is deliberately outside the two real-positive proofs.
   _need(_integer(s['raw']['0x170'])==0)
   raw=_integer(s['raw']['0x180'],1)
   casualties[key]=raw/100000;raws[key]=raw
  _need(set(casualties)=={'our_org_loss','enemy_org_loss'})
  return {'combat_id':combat_id,'casualties':casualties,'raw_ground_org_loss':raws,
          'scope':'native cumulative ground organization points, currentCombatant lifecycle; captured air_org==0; no manpower proof; no historical-ID/result/time proof'}
 except (KeyError,TypeError,ValueError,IndexError):
  return None

def load(path):
 return json.loads(Path(path).read_text(encoding='utf-8'))
