"""Research-only frozen exclusions and named supply-threshold leaf.
No national needed or crisis export; no game/process/save access.
"""
import hashlib,struct
BASE=0x7ff758fc0000
class Unproved(ValueError):pass
def need(x,s):
 if not x:raise Unproved(s)
CODE={
 't226_named_national_manpower_consumers.json':{'0xd5e2f0':'689bafc433319f097c0ce3c22b99ccb77fe6fd7b58f7683032fb7d64f5863755'},
 't226_named_reinforcement_consumers.json':{'0x15a6eb0':'87a5daf68dff0066f310aad08a930a3f2d63fe321f4d39aa1f16ce3e6307d92c'},
 't226_named_supply_alert_consumers.json':{'0xb50ab0':'eac9d4a813627453b0005929c55317000e3b8a2df34fee540fa67c2a61793ad5'},
 't226_supply_define_registry_helpers.json':{'0x9ed730':'d40ec5e68d91803a5b95b57cd8009e710b205f90413a050d6b115e7739c5b006','0x9eda80':'52de74e14f91448ef4278a6e6d32b392eaa1358a0efaa5ba796425030cf8ba1e'},
 't226_supply_alert_threshold_leaf.json':{'0x16d8d50':'4df9789d562e42bad6e921af6f62a122778be0c6028435b9d4fe896210ee806c'}}
LIVE='t226_live_per_unit_non_substitution_control.json';BIND='t226_supply_define_raw_binding.json'
class Frozen:
 def __init__(self,d):
  self.b={}
  for row in d['raw_dependencies']:
   b=bytes.fromhex(row['hex']);a=int(row['address'],16);need(len(b)==row['size'],'raw length')
   for j,v in enumerate(b):need(a+j not in self.b or self.b[a+j]==v,'raw overlap');self.b[a+j]=v
 def read(self,a,n):
  try:return bytes(self.b[a+j] for j in range(n))
  except KeyError:raise Unproved('missing frozen operand')
 def q(self,a):return struct.unpack('<Q',self.read(a,8))[0]
 def i(self,a):return struct.unpack('<i',self.read(a,4))[0]
def native_bucket(value,low=50000,very=20000):
 need(type(value) is int and -(1<<63)<=value<(1<<63),'signed native qword')
 need(type(low) is int and type(very) is int and 0<=very<=low<=100000,'ordered native thresholds')
 return 0 if value<very else 2 if value>=low else 1
def qualified_bucket(value):
 need(type(value) is int and 0<=value<=100000,'ratio acceptance narrower than native signed leaf')
 return native_bucket(value)
def export_national_needed(*args,**kwargs):raise Unproved('no independently proved national reinforcement-men consumer; per-unit sum forbidden')
def export_crisis(*args,**kwargs):raise Unproved('threshold/name registration lacks subject/predicate/live-positive/schema proof')
def replay(d):
 need(all(n in d for n in (*CODE,LIVE,BIND,'t226_national_getter_classification.json')),'required independent evidence')
 baseline=None
 for n in (*CODE,LIVE,BIND):
  doc=d[n];g=doc['before'];need(g==doc['after'],'unstable guard');need(baseline is None or baseline==g,'mixed sessions');baseline=g
  need(g['pid']==10288 and g['base']==hex(BASE) and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values()),'session gate')
 fs={}
 for n,rows in CODE.items():
  for a,h in rows.items():
   f=d[n]['functions'][a];need(not f['unresolved_edges'],'native CFG open');need(f['sha256']==h and hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()==h,'native code integrity');fs[a]=f
 def atoms(a,*ss):need(all(s in fs[a]['asm'] for s in ss),'semantic atom missing')
 atoms('0xd5e2f0','d5e6c8 lea rdx, [rip + 0x1c7d1d9]','d5e3d1 call 0xd5c3d0','d5e3de call 0xd5c490','d5e41d lea eax, [rdi + rbx]')
 names=d['t226_national_getter_classification.json']['ui_argument_names'];need({x['text'] for x in names}=={'GARRISON','NAVAL_TRAINING','NAVAL_FIELD','NAVAL','AIR','TRAINING','FIELD','ARMY','EXILE','FREE','MANPOWER_USAGE'},'national usage breakdown not reinforcement need')
 atoms('0x15a6eb0','15a7030 lea rcx, [rbx + 0x3d0]','15a7037 call 0xcc64e0','15a704c call 0xcc5ef0','15a7051 sub edi, eax','15a7101 call 0xd5dae0','15a7109 cmovg r13d, eax','15a7117 cmovg r13d, r14d','15a7766 lea rdx, [rip + 0x14a45bb]')
 atoms('0xb50ab0','b510c3 lea rdx, [rip + 0x1e72866]','b510de mov edx, 3','b510e6 call 0xb61660','b5113c lea rdx, [rip + 0x1e72805]','b51157 mov edx, 4','b5115f call 0xb61660')
 atoms('0x16d8d50','16d8d52 cmp rcx, qword ptr [rip + 0x1d0a767]','16d8d59 jl 0x16d8d67','16d8d5b cmp rcx, qword ptr [rip + 0x1d0a85e]','16d8d62 setge al','16d8d65 inc eax')
 bind=d[BIND];bm=Frozen(bind);need(len(bind['cells'])==2,'two actual define bindings');values={}
 for c,name,glob,vt,helper,leaf,lr in zip(bind['cells'],('ALERT_LOW_SUPPLY_LEVEL','ALERT_VERY_LOW_SUPPLY_LEVEL'),(0x33e35c0,0x33e34c0),(0x29a5cf8,0x29a5ba8),(0x9ed730,0x9eda80),(0x7924a0,0x7924b0),(0x29a5da8,0x29a5c60)):
  need(c['name']==name and int(c['name_rva'],16)==lr and bm.read(BASE+lr,len(name)+1)==name.encode()+b'\0','raw define key')
  need(c['value_rva']==hex(glob) and c['vtable_rva']==hex(vt) and c['name_leaf']==hex(leaf) and c['load_helper']==hex(helper),'define identity')
  raw=bm.read(BASE+glob,8);value=struct.unpack('<q',raw)[0];need(raw.hex()==c['value_raw_hex'] and value==c['value'],'raw cached define value')
  vr=bm.read(BASE+vt,16);need(c['vtable_actual_slot_count']==2 and vr.hex()==c['two_actual_slots_hex'] and struct.unpack('<QQ',vr)==(BASE+helper,BASE+leaf),'only two valid vtable slots; following data is not callable')
  f=fs[hex(helper)];b=bytes.fromhex(f['raw_hex']);need(helper+0x1ab+7+struct.unpack_from('<i',b,0x1ab+3)[0]==glob,'helper destination RIP');need(helper+0x1b2+7+struct.unpack_from('<i',b,0x1b2+3)[0]==lr,'helper named key RIP');values[name]=value
 need(values=={'ALERT_LOW_SUPPLY_LEVEL':50000,'ALERT_VERY_LOW_SUPPLY_LEVEL':20000},'observed thresholds');need(bind['actual_supply_alert_positive_samples']==0 and bind['schema_promotions']==[],'no live crisis positive or promotion')
 live=d[LIVE];lm=Frozen(live);country=int(live['before']['country'],16);up,cap,n=struct.unpack('<QII',lm.read(country+0x290,16));need(n==live['own_registry_count']==49 and 0<n<=cap<=10000,'own registry count');need(live['inspection_limit']==8 and live['inspected']==len(live['rows'])==8<n,'bounded eight, not national census')
 controls=[]
 for j,row in enumerate(live['rows']):
  u=lm.q(up+j*8);need(u==int(row['pointer'],16) and row['ordinal']==j,'fresh subject join');need(lm.i(u+0x18)==row['handle_type']==51 and lm.i(u+0x1c)==row['unit_id'] and lm.i(u+0x1e0)==row['owner_tag']==3,'CArmy handle/owner');mp=u+0x3d0;need(lm.q(mp+0x48)==u,'manpower backlink')
  sums=[]
  for off,key in ((0x10,'current_by_country'),(0x30,'engine_need_by_country')):
   ptr,cap,count=struct.unpack('<QII',lm.read(mp+off,16));need(0<=count<=cap<=256,'nationality table bounds');pairs=[{'country_index':a,'amount':v} for a,v in struct.iter_unpack('<ii',lm.read(ptr,count*8))];need(all(x['country_index']>=0 and x['amount']>=0 for x in pairs) and len({x['country_index'] for x in pairs})==len(pairs),'valid per-unit nationalities');need(pairs==row[key],'per-unit raw table');sums.append(sum(x['amount'] for x in pairs))
  current,full=sums;missing=max(full-current,0);need(current==row['current'] and full==row['engine_need_total'] and missing==row['engine_missing_formula'],'raw requirement/current/missing distinction');controls.append({'unit_id':row['unit_id'],'current':current,'full_requirement':full,'missing':missing})
 need(all(r['full_requirement']>0 and r['missing']==0 for r in controls),'actual full requirement is NOT missing positive');need(not live['national_needed_proved'] and not live['unit_sum_exported_as_national_needed'],'national substitution forbidden')
 return {'per_unit_controls':controls,'sample_is_national_census':False,'national_needed_exported':False,'crisis_exported':False,'native_supply_thresholds':values,'actual_national_needed_positive_samples':0,'actual_supply_alert_positive_samples':0,'promoted_fields':[],'complete_input':False,'next':'B58150 calls16D8D50 atB5825A/B585CA; prove actual subject/current-ratio/alert3-4 predicate and live positive before any crisis field promotion'}
