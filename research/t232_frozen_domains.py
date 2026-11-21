"""Frozen restarted-session semantic rejection certificate. No process or IO backend."""
import hashlib,struct
class Unproved(ValueError):pass
def need(x,s):
 if not x:raise Unproved(s)
class Frozen:
 def __init__(self,d):
  self.b={}
  for row in d['raw_dependencies']:
   a=int(row['address'],16);raw=bytes.fromhex(row['hex']);need(len(raw)==row['size'],'dependency size')
   for i,v in enumerate(raw):need(a+i not in self.b or self.b[a+i]==v,'dependency conflict');self.b[a+i]=v
 def read(self,a,n):
  try:return bytes(self.b[a+i] for i in range(n))
  except KeyError:raise Unproved('missing dependency')
 def q(self,a):return struct.unpack('<Q',self.read(a,8))[0]
 def i(self,a):return struct.unpack('<i',self.read(a,4))[0]
 def string(self,a):
  b=self.read(a,32);n,c=struct.unpack_from('<QQ',b,16);need(0<=n<=c<1048576,'string bound');return (b[:n] if c<=15 else self.read(struct.unpack_from('<Q',b)[0],n)).decode()
 def array(self,a,limit):
  p,c,n=struct.unpack('<QII',self.read(a,16));need(0<=n<=c<=max(4096,limit) and n<=limit,'array bound');return [self.q(p+i*8) for i in range(n)]
INV='8213d5be560adf5565e8244f45e16fc2e5aa987ad2dbbc8ccf057939dd18cbf3'
BASE=0x7ff72fc80000
NAMES={19364:'alert_level',19365:'low',19366:'medium',19367:'high',19369:'alert_margin'}
def replay(session,domain,level,tokens,pivot,pins,inventory,claims=None):
 claims=claims or {};g=session['before']
 need(g['pid']==31576 and int(g['base'],16)==BASE and g['country_index']==3,'restarted identity')
 need(g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values()),'session safety')
 need(session['safe_to_research'] and session['version']=='1.19.5.0.7c6c' and session['country_tag']=='SOV','session acceptance')
 need(session['production_hashes_match'] and session['native_controls_match'],'fingerprints')
 for doc in (session,domain,level,tokens,pivot):need(doc['before']==doc['after']==g,'mixed/stale session')
 need(hashlib.sha256(inventory).hexdigest()==INV,'inventory')
 fs=dict(domain['functions']);fs['0x145e1c0']=domain['candidate_functions']['0x145e1c0'];fs['0x253ecd0']=tokens['getter_flow']
 for a,pin in pins.items():
  f=fs[a];need(f['window_size']==pin['window_size'] and f['sha256']==pin['sha256']==hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest(),'native integrity')
  if a!='0x145e1c0':need(not f['unresolved_edges'] and not f['external_tails'],'closed required body')
 need(len(fs['0x145e1c0']['unresolved_edges'])==5 and len(fs['0x145e1c0']['external_tails'])==9,'parser partial retained')
 def atoms(a,*lines):need(all(s in fs[a]['asm'] for s in lines),'semantic atoms')
 table=struct.unpack('<3Q',bytes.fromhex(domain['current_table_hex']));sig,off,cd,td,chd,selfrva=struct.unpack('<6I',bytes.fromhex(domain['current_col_hex']))
 need(sig==1 and off==0x18 and table[0]==BASE+selfrva and domain['class']=='.?AVCNavyTheaterGroupItem@@','navy secondary identity')
 need(table[1]-BASE==0x1eeff60 and table[2]-BASE==0x1eefb08 and domain['method1_rva']=='0x1eefb08','corrected pointer arithmetic')
 atoms('0x1eefb08','1eefb08 sub rcx, 0x18','1eefb0c jmp 0x1eefb60','1eefb85 mov qword ptr [rcx + 0x18], rax')
 atoms('0x1eeff60','1eeff84 add rcx, 0x30','1eeff97 call 0x2284870','1eeffc0 cmp byte ptr [rax + 0x58], 0','1eeffc4 cmovne rdx, rcx')
 lit={x['text'] for x in fs['0x1eeff60']['reachable_literals']};need({'ALERT_PRIORITY_HIGH','ALERT_PRIORITY_NORMAL','ALERT_PRIORITY_DETAILS'}<=lit,'named priority consumer')
 identities=level['parser_slot_identities'];need(len(identities)==1 and identities[0]['class']=='.?AVCOccupationModifier@@' and identities[0]['slot_offset']=='0x20','occupation parser identity')
 atoms('0x145e1c0','145e3ad sub edx, 0x4ba4','145e3b3 je 0x145e3db','145e3db mov edx, dword ptr [rbx + 0xc0]','145e3e1 sub edx, 0x4ba5','145e4d4 mov dword ptr [rcx + 0xc8], 0','145e4c4 mov dword ptr [rcx + 0xc8], 1','145e4b4 mov dword ptr [rcx + 0xc8], 2')
 tm=Frozen(tokens);init=tm.read(BASE+0x368f570,1);count=tm.i(BASE+0x368f574);tp=tm.q(BASE+0x368f5a0)
 need(init==b'\x01' and 19369<count<100000,'initialized token bound')
 actual={n:tm.string(tp+n*32) for n in NAMES};need(actual==NAMES,'live token strings')
 lm=Frozen(level);country=int(g['country'],16);theatre=lm.array(country+0x168,64)[0];tg=lm.array(theatre+0xc8,128)[0];og=lm.array(tg+0x48,128)[0];members=lm.array(og+0x50,256)
 need(len(members)==level['native_member_count']==25 and level['sampled_members']==3 and level['new_units_inspected']==0,'three member scope')
 by={}
 for member in members[:3]:
  u=member-0xb8;need(lm.i(u+0x18)==51 and lm.i(u+0x1e0)==3 and lm.q(u+0xc0)==og,'unit membership')
  uid=lm.i(u+0x1c);by[uid]={'source':struct.unpack('<q',lm.read(u+0x40,8))[0],'province':lm.i(u+0x28)}
 need(set(by)=={500,374,479} and by[479]=={'source':11335,'province':1780} and by[374]['source']==100000,'live witness controls')
 manager=lm.q(int(g['idler'],16)+0x7a8);keys={};values={}
 for aid in (3,4):
  p,c,n=struct.unpack('<QII',lm.read(manager+(aid+0xf0e)*24,16));need(0<=n<=c<=32,'active bounds');rows=[]
  values[aid]=lm.i(manager+aid*0x468+0x448)
  for j in range(n):
   ep=p+j*0x468;k=struct.unpack('<4Q',lm.read(ep+0x438,32));rows.append((k[0],k[1],k[3]));need(lm.i(ep+0x448)==5,'raw registration flag')
  keys[aid]=rows
 need((0,tg,0) in keys[4] and (0,tg,0) not in keys[3],'qualified cached witness')
 need(values=={3:5,4:5},'same registration values not levels')
 need(not claims.get('severity_from_priority') and not claims.get('severity_from_occupation_enum') and not claims.get('severity_from448'),'no schema severity mapping')
 need(not claims.get('full_feed') and not claims.get('notes_read'),'no scope expansion')
 need(not claims.get('front_invalidated_from_log'),'no invalidation from log')
 return {'promotions':[],'priority_domain':'navy UI secondary interface','alert_level_domain':'occupation modifier definition','native_occupation_enum':{'low':0,'medium':1,'high':2},'schema_severity_samples':0,'sampled_members':3,'native_member_count':25,'qualified_witness_unit_ids':[479],'healthy_control_unit_ids':[374],'front_invalidated_samples':0,'parser_globally_closed':False}
