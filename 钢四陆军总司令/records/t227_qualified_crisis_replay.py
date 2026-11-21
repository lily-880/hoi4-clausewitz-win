"""t227 frozen qualified crisis evidence; no process/game/backend or production integration.
Schema-kind annotation combines independently proved native alert + out-of-supply,
not a raw native Crisis object. Severity/notes/complete records stay unproved.
"""
import hashlib,struct
BASE=0x7ff758fc0000
class Unproved(ValueError):pass
CODE={'t227_supply_alert_updater.json': {'0xb58150': '2706e302d98a24343083522b77c01a5c7149e69a9a47e4dba3976dfb04e16368'}, 't227_supply_alert_mapping_consumers.json': {'0xb79d00': '2945c5fbc9fbcd3966ac0d44f5bd6385fae3634cb5f1d7f82b9c7a650ce9360d', '0xb867b0': '70fa20743b1058b4e72558864d48e3459353d497275d78e9dec24f1c784572a6'}, 't227_supply_subject_registry_chain.json': {'0x717210': '99409c77c8a79d86037f2859bdfeb9603a02e9a237836136f9f1deb807ddad7b', '0x7413e0': '27c9ea27c2a60040853240d709ed75c38967c29e0cc2011d103f83a648ec2484', '0xd84a10': 'f4ca3638055acbeb8bf7755771930771c47a9773ef980e1ed40bd5293a3077b5'}, 't227_land_alert_membership_and_handlers.json': {'0xd73190': 'd36eb16de65b53a965c8017cc2037ccf09746797dee21c4bb84f57db94a3d730', '0xce4cd0': '69fcbcbefec80a0ebd22b726de3734a612f6a97e9f2f4535a04f00b7664dc018', '0xb54c00': 'c17cb6c5ef73bd9406ba7deab730a1a97bf60b8ba5947c7dfc44974843138bbe', '0xb6a2b0': '467544e56db81acce097a32ddac5a0b861e3d2eae044b7a2f84a7ef7b98af586'}, 't227_land_group_receiver_binding.json': {'0xd3cb00': 'e4fa3ebc6d79900d4c19a28d10e963039f2bfaa9a2a1083dd6b8ccc9f4d140c6'}, 't227_land_member_virtual_adjustments.json': {'0xc4f050': '126d26f019f2a5f7f14a33e2850a7c83de3fce95d9f0b5e9508ce11836fcbb7e', '0x20f350': '4432bbb677ed13a091028dedcf1aa90ac4fa9d3d34971f347d83b3506c864ace'}, 't227_live_land_alert_controls.json': {'0xce4f10': 'b645a9ac6d78d83bba08574a7ae11973a78e46195c6d67361e9a5772286589a6'}}
PARTIAL_ROOT_HASH='bacdbdf7a9ffe5023b9fcfefbd91ed1ffdb3f2edbde8d1584e419e981cd9ab74'
PREFIX_HASHES={'0xe41670': '9d3dd0402fcbb702ad6d6890a2a8f879c3713ea90887694af659e853142f5251', '0xe4abf0': '7445e35fecedc6f62753081a337598fa5307931f12da28a1791ce47903397033'}
LIVE='t227_live_land_alert_controls.json';ACTIVE='t227_live_active_alert_group_binding.json'
def need(x,s):
 if not x:raise Unproved(s)
class Frozen:
 def __init__(self,d):
  self.b={}
  for row in d['raw_dependencies']:
   a=int(row['address'],16);b=bytes.fromhex(row['hex']);need(len(b)==row['size'],'raw size')
   for j,v in enumerate(b):need(a+j not in self.b or self.b[a+j]==v,'overlap conflict');self.b[a+j]=v
 def read(self,a,n):
  try:return bytes(self.b[a+j] for j in range(n))
  except KeyError:raise Unproved('missing raw dependency')
 def q(self,a):return struct.unpack('<Q',self.read(a,8))[0]
 def i(self,a):return struct.unpack('<i',self.read(a,4))[0]
 def sq(self,a):return struct.unpack('<q',self.read(a,8))[0]
 def array(self,a,bound):
  p,c,n=struct.unpack('<QII',self.read(a,16));need(0<=n<=c<=max(4096,bound) and n<=bound,'array bound');return [self.q(p+j*8) for j in range(n)]
 def string(self,a):
  b=self.read(a,32);n,c=struct.unpack_from('<QQ',b,16);need(0<=n<=c<=1024,'string bound');return (b[:n] if c<=15 else self.read(struct.unpack_from('<Q',b)[0],n)).decode('utf-8')
def bucket(v):
 need(type(v) is int and -(1<<63)<=v<(1<<63),'native signed qword')
 return 0 if v<20000 else 2 if v>=50000 else 1
def supply(source,capacity,reserve,hours,threshold,special):
 need(type(special) is bool and type(hours) is int and 0<hours<=100000 and 0<=threshold<=100000,'supply globals')
 need(-100000<=source<=10**9 and capacity>=0 and 0<=reserve<=(2**63-1)//100000,'accepted supply arithmetic')
 effective=max(0,min(100000,max(source,reserve//hours))) if capacity>0 else 0
 out=False if special else effective<threshold
 native=2 if special else min(bucket(source),bucket(effective))
 return effective,out,native
def qualifies(native,out,special):return native==0 and out and not special

def replay(d):
 needed=(*CODE,LIVE,ACTIVE,'t227_live_registry_type_bindings.json','t227_alert_manager_update_root.json')
 need(all(n in d for n in needed),'independent evidence absent');baseline=None
 for n in needed:
  doc=d[n];g=doc['before'];need(doc['after']==g,'unstable guard');need(baseline is None or baseline==g,'mixed session');baseline=g
  need(g['pid']==10288 and g['base']==hex(BASE) and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values()),'session gate')
 fs={}
 for n,aa in CODE.items():
  for a,h in aa.items():
   f=d[n]['functions'][a];need(not f['unresolved_edges'],'open required native CFG');need(f['sha256']==h and hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()==h,'native integrity');fs[a]=f
 def atoms(a,*ss):need(all(s in fs[a]['asm'] for s in ss),'native semantic dataflow')
 atoms('0xb58150','b581ec call 0x717210','b58223 call 0xd84a10','b58256 mov rcx, qword ptr [rbx + 0x40]','b5825a call 0x16d8d50','b58504 call 0x7413e0','b585aa mov rax, qword ptr [rdi + 0x30]','b585bb cmp qword ptr [rbx + 0x20], 0','b585c6 mov rcx, qword ptr [rbx + 0x30]','b585ca call 0x16d8d50')
 atoms('0xb867b0','b86832 call 0xb58150','b86ca6 cmp esi, 1','b86ca9 setne dl','b86cac add edx, 5','b86cc2 call 0xb54c00')
 types=d['t227_live_registry_type_bindings.json']['rows'];need(types[0]['first_class']=='.?AVCFleet@@' and types[1]['first_class']=='.?AVCTaskForce@@' and types[5]['country_object_class']=='.?AVCStrategicAir@@' and types[6]['first_class']=='.?AVCAirBase@@','actual original domains')
 atoms('0xd3cb00','d3cb00 lea rax, [rcx + 0xc8]');atoms('0xd73190','d73190 lea rax, [rcx + 0x48]')
 atoms('0xc4f050','c4f050 lea rax, [rcx - 0xb8]');atoms('0x20f350','20f350 mov rax, rcx')
 atoms('0xb79d00','b79d39 call 0xd73190','b79d64 mov rdi, qword ptr [rax + 0x50]','b79d7b call qword ptr [rax + 0x20]','b79d93 call qword ptr [rax + 0x40]','b79da5 cmp qword ptr [rax + 0x2f8], 0','b79dba call 0x16d8d50','b79dc9 call 0xce4cd0','b79dd1 call 0x16d8d50','b79dd8 cmovl ebx, eax','b79ddd cmovl ebx, esi','b79e17 mov edx, 4','b79e23 call 0xb54c00','b79e2b mov edx, 3','b79e65 call 0xb6a2b0')
 atoms('0xce4f10','ce4f10 cmp qword ptr [rcx + 0x2f8], 0','ce4f1d xor al, al','ce4f96 cmp rax, qword ptr [rip + 0x26fee63]','ce4f9d setl al')
 root=d['t227_alert_manager_update_root.json']['functions']['0xb6b9e0'];need(root['sha256']==PARTIAL_ROOT_HASH and hashlib.sha256(bytes.fromhex(root['raw_hex'])).hexdigest()==PARTIAL_ROOT_HASH,'partial root bytes');need(bool(root['unresolved_edges']),'dispatcher is partial, NOT globally closed')
 need(all(s in root['asm'] for s in ('b6bbd0 mov rcx, qword ptr [rdi + 0x168]','b6bbdb call 0xd3cb00','b6bc1c mov rdx, r9','b6bc22 call 0xb79d00')),'caller receiver path')
 active=d[ACTIVE];am=Frozen(active);idler=int(active['before']['idler'],16);manager=am.q(idler+0x7a8);need(manager==int(active['manager'],16),'fresh manager root')
 for a,h in PREFIX_HASHES.items():
  f=active['entry_prefixes'][a];need(f['sha256']==h and hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()==h,'idler this-binding prefix')
 need('0xe41698 mov r13, rcx' in active['entry_prefixes']['0xe41670']['asm'] and '0xe4ac10 mov r12, rcx' in active['entry_prefixes']['0xe4abf0']['asm'],'canonical idler this register')
 names={'3':'alert_low_supply','4':'alert_very_low_supply','5':'alert_base_low_supply','6':'alert_base_very_low_supply'}
 need(active['names']==names,'actual alert names/IDs')
 for aid,name in names.items():need(am.string(manager+int(aid)*0x468+0x410)==name,'raw named manager')
 live=d[LIVE];lm=Frozen(live);country=int(live['before']['country'],16);membership=live['membership'];need(len(membership)==1,'one qualified OrdersGroup entrance');m=membership[0];tp=int(m['theatre'],16);tg=int(m['theater_group'],16);og=int(m['orders_group'],16)
 need(tp in lm.array(country+0x168,64) and tg in lm.array(tp+0xc8,128) and og in lm.array(tg+0x48,128),'native TheaterGroup membership');members=lm.array(og+0x50,256);need(len(members)==m['member_count']==25,'member count not full feed');need(active['current_theater_group']==hex(tg),'same cached group')
 cached={}
 for aid in (3,4):
  ptr,cap,n=struct.unpack('<QII',am.read(manager+(aid+0xf0e)*24,16));a=active['active'][str(aid)];need(n==a['count'] and n<=cap<=128 and len(a['rows'])==n,'cached active header');keys=[]
  for j,entry in enumerate(a['rows']):
   ep=ptr+j*0x468;key=struct.unpack('<QQQQ',am.read(ep+0x438,32));need(hex(ep)==entry['entry'] and (hex(key[0]),hex(key[1]),hex(key[3]))==(entry['key0'],entry['key_group'],entry['key3']),'cached keys');need(am.string(ep+0x410)==names[str(aid)]==entry['name'],'cached active name');keys.append((key[0],key[1],key[3]))
  cached[aid]=keys
 need((0,tg,0) in cached[4] and (0,tg,0) not in cached[3],'actual native alert4 present and3 absent for qualified group')
 need(live['thresholds']=={'low':50000,'very_low':20000} and lm.sq(BASE+0x33e35c0)==50000 and lm.sq(BASE+0x33e34c0)==20000,'native alert thresholds')
 need(live['inspection_limit']==64 and live['inspected']==len(live['rows'])==3<len(members),'bounded three controls, not complete list')
 by={};audit=[]
 for j,row in enumerate(live['rows']):
  member=members[j];u=member-0xb8;need(member==int(row['member'],16) and u==int(row['army'],16),'fresh ordinal join');need(lm.q(lm.q(member)+0x20)==BASE+0xc4f050 and lm.q(lm.q(u)+0x40)==BASE+0x20f350,'actual virtual adjustments')
  uid=lm.i(u+0x1c);need(uid==row['unit_id'] and uid not in by and lm.i(u+0x18)==row['handle_type']==51 and lm.i(u+0x1e0)==row['owner_tag']==3,'unit handle/owner');need(lm.q(u+0xc0)==og and row['orders_group']==hex(og) and row['theater_group']==hex(tg),'ordersgroup backlink')
  pp=lm.q(u+0x1f0);pid=lm.i(u+0x28);need(pp==int(row['province'],16) and pid==row['province_id']==lm.i(pp+0xa4),'current province join')
  source=lm.sq(u+0x40);capacity=lm.sq(u+0x600);reserve=lm.sq(u+0x610);special=bool(lm.q(u+0x2f8));hours=lm.i(BASE+0x33e3678);threshold=lm.sq(BASE+0x33e3e00);effective,out,native=supply(source,capacity,reserve,hours,threshold,special);ev=row['supply_evidence']
  need((source,effective,special,native,not out)==(row['source_raw'],row['effective_raw'],row['special_present'],row['native_alert_bucket'],row['in_supply']),'raw supply and native alert recomputation');need((reserve,capacity,hours,threshold)==(ev['reserve_raw'],ev['capacity_raw'],ev['buffer_parameter'],ev['threshold_raw']),'raw supply operands');entry={'unit_id':uid,'province_id':pid,'source':source,'effective':effective,'native_bucket':native,'out_of_supply':out,'special':special};by[uid]=entry;audit.append(entry)
 need(set(by)=={500,374,479},'actual control identities');need(live['positive']['unit_id']==479 and live['negative']['unit_id']==374,'genuine selected controls');need(by[479]['native_bucket']==0 and by[479]['out_of_supply'] and by[374]['native_bucket']==2 and not by[374]['out_of_supply'],'genuine positive-negative contrast')
 # Bucket0 is the native minimum, so this witness proves group minimum0 even
 # without reading all remaining members. Do not emit whole-group IDs.
 witness=by[479];need(qualifies(witness['native_bucket'],witness['out_of_supply'],witness['special']),'dual independent semantic qualification')
 return {'qualified_evidence':[{'kind':'out_of_supply','unit_ids':[479],'province_ids':[witness['province_id']]}],'control_audit':audit,'native_group_alert_id':4,'native_group_minimum':0,'kind_is_composed_schema_annotation_not_raw_Crisis_enum':True,'severity_exported':False,'notes_exported':False,'complete_crisis_record':False,'complete_crisis_feed':False,'complete_input':False,'scope':'current own TheaterGroup, actual cached alert4; sampled type51 causal bucket0/out-of-supply witness only; not every group member or complete input'}
