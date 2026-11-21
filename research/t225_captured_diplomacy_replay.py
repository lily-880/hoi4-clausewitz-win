"""Machine-specific frozen native diplomacy proof, NOT a production relation exporter.
No process access; false war/same-faction predicates never manufacture schema ally.
"""
import hashlib,struct
class Unproved(ValueError):pass
BASE=0x7ff758fc0000
CODE={
 't225_named_trigger_evaluators.json':{'0x3f79e0':'fdbb3a6200f23da6511eec246cb54cca43031230888161c2206a6792d68eab74','0x3f90f0':'9ccae98fcaa0b856cb1f4124fdcc22302972ac693af50ea00c6b7c1071f77f43'},
 't225_tag_remap_closed.json':{'0xc08790':'ef09ab54ede7f054301a2f43b68b8a85ae2bc52586245e530b2f4cc753c50df7'},
 't225_tag_lookup_and_war_getter.json':{'0xc07bf0':'afd87dbad7096cd8681ec29156ca9b34b8079906f53547b2c3f7426409f1d8e5','0x748400':'79736a01b862150b0a17edad56931ac59d7fa135508bff8914507ae804197ae1'},
 't225_war_faction_named_tooltips.json':{'0x439cc0':'2d8b6b210927544d93cc793cfe7d62b10f9d10a80103c7066eb7c9cf133ec94d','0x43eb90':'d3fbc3e7401961fdee1e27094b49dc98605c2cfdef0664e79dd32784d6faab99'}}
LIVE='t225_live_diplomacy_contrast.json'
BIND='t225_raw_named_binding_and_subject_join.json'
def need(ok,why):
 if not ok:raise Unproved(why)
class Frozen:
 def __init__(self,doc):
  self.b={}
  for row in doc['raw_dependencies']:
   a=int(row['address'],16);b=bytes.fromhex(row['hex']);need(len(b)==row['size'],'raw size')
   for j,v in enumerate(b):
    need(a+j not in self.b or self.b[a+j]==v,'overlapping raw conflict');self.b[a+j]=v
 def read(self,a,n):
  try:return bytes(self.b[a+j] for j in range(n))
  except KeyError:raise Unproved('missing frozen operand')
 def q(self,a):return struct.unpack('<Q',self.read(a,8))[0]
 def i(self,a):return struct.unpack('<i',self.read(a,4))[0]
def at_war(wp,flag):
 need(type(wp) is int and wp>=0,'war pointer')
 if not wp:need(flag is None,'absent war cannot have a flag');return False
 need(type(flag) is int and 0<=flag<=255,'native byte49 required')
 return flag==0
def same_faction(a,b):
 need(type(a) is int and type(b) is int and a>=0 and b>=0,'faction pointers')
 return a!=0 and b!=0 and a==b
def candidate(war,is_self=False):
 need(type(war) is bool and type(is_self) is bool,'boolean predicates')
 need(not(war and is_self),'self war contradiction')
 return 'self' if is_self else 'enemy' if war else 'unknown'
def replay(docs):
 need(all(n in docs for n in (*CODE,LIVE,BIND,'t225_named_trigger_vtables.json')),'independent semantic evidence missing')
 baseline=None
 for n in (*CODE,LIVE,BIND,'t225_named_trigger_vtables.json'):
  d=docs[n];g=d['before'];need(d['after']==g,'unstable guard');need(baseline is None or baseline==g,'mixed session');baseline=g
  need(g['pid']==10288 and g['base']==hex(BASE) and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values()),'session gate')
 fs={}
 for n,entries in CODE.items():
  for a,h in entries.items():
   f=docs[n]['functions'][a];need(not f['unresolved_edges'],'unclosed native CFG');need(f['sha256']==h and hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()==h,'code integrity');fs[a]=f
 def atoms(a,*ss):need(all(s in fs[a]['asm'] for s in ss),'native semantic dataflow missing')
 atoms('0x3f79e0','3f7a05 call 0xc07bf0','3f7a21 call 0xc08790','3f7a31 mov rax, qword ptr [rcx + 0x2e8]','3f7a3d cmp byte ptr [rax + 0x49], 0','3f7a41 jne 0x3f7a4b','3f7a43 mov al, 1')
 atoms('0x3f90f0','3f9122 cmp qword ptr [rcx + 0x2d8], 0','3f912a je 0x3f9180','3f9169 mov rax, qword ptr [rcx + 0x2d8]','3f9170 cmp qword ptr [rbx + 0x2d8], rax','3f9177 sete al')
 atoms('0xc08790','c08848 mov rax, qword ptr [rcx + 0x340]','c0884f mov eax, dword ptr [rax + rdx*4]')
 atoms('0xc07bf0','c07d07 mov rax, qword ptr [rdi + 0x310]','c07d0e mov rax, qword ptr [rax + rcx*8]')
 atoms('0x748400','748452 mov rax, qword ptr [rax + 0x2e8]','74845e cmp byte ptr [rax + 0x49], 0')
 bm=Frozen(docs[BIND]);bindings=docs[BIND]['bindings'];vr=docs['t225_named_trigger_vtables.json']['rows'];need(len(bindings)==len(vr)==2,'two independent named consumers')
 specs=((0x280bbe0,0x439cc0,0x3f79e0,0x280bcc0,'TRIGGER_HAS_WAR_WITH'),(0x280f220,0x43eb90,0x3f90f0,0x280f300,'TRIGGER_IS_IN_FACTION_WITH'))
 for v,tip,ev,lr,name in specs:
  row=next((r for r in bindings if int(r['vtable_rva'],16)==v),None);meta=next((r for r in vr if int(r['vtable_rva'],16)==v),None);need(row is not None and meta is not None,'vtable binding absent')
  need(row['literal']==name and int(row['literal_rva'],16)==lr,'wrong named tooltip');need(row['evaluation_slot']=='0xb0' and row['tooltip_slot']=='0xa8','slot identity')
  need(bm.read(BASE+lr,len(name)+1)==name.encode()+b'\0','raw localization name')
  col=bm.q(BASE+v-8);sig,off,cd,td,ch,sr=struct.unpack('<6I',bm.read(col,24));need(sig==1 and off==0 and sr==col-BASE and sr==int(row['col_rva'],16) and td==int(row['type_descriptor_rva'],16),'RTTI COL link')
  need(bm.read(BASE+td+16,len(row['class_name'])+1)==row['class_name'].encode()+b'\0','raw RTTI identity')
  need(bm.q(BASE+v+0xa8)==BASE+tip and bm.q(BASE+v+0xb0)==BASE+ev,'tooltip/evaluator same vtable')
  need(int(meta['tooltip_function'],16)==tip and meta['tooltip_slot']=='0xa8' and int(meta['slots'][22]['target'],16)==ev,'recorded vtable metadata')
  site=0x439d14 if tip==0x439cc0 else 0x43ebe4
  raw=bytes.fromhex(fs[hex(tip)]['raw_hex']);disp=struct.unpack_from('<i',raw,site-tip+3)[0];need(site+7+disp==lr,'tooltip RIP literal association')
 live=docs[LIVE];need(live['version']=='1.19.5.0.7c6c','version');lm=Frozen(live);gs=int(live['before']['gs'],16);table=lm.q(gs+0x310);remap=lm.q(gs+0x340);countries=live['countries'];need(set(countries)=={'1','3','16','368'},'bounded country set')
 for key,c in countries.items():
  idx=int(key);cp=lm.q(table+idx*8);need(cp==int(c['country'],16) and lm.i(cp+8)==c['tag'] and lm.i(remap+c['tag']*4)==idx,'country tag/remap join')
  dp=lm.q(cp+0xf88);need(dp==int(c['diplomacy'],16) and lm.q(dp+0x2d8)==int(c['faction'],16),'country diplomacy/faction operand')
 results=[]
 for p in live['pairs']:
  s=countries[str(p['source_index'])];t=countries[str(p['target_index'])];need((p['source_tag'],p['target_tag'])==(s['tag'],t['tag']),'pair tag identity');dp=int(s['diplomacy'],16);rp=lm.q(lm.q(dp+8)+t['index']*8);need(rp and rp==int(p['relation'],16),'named trigger nonnull relation receiver');wp=lm.q(rp+0x2e8);flag=lm.read(wp+0x49,1)[0] if wp else None
  war=at_war(wp,flag);faction=same_faction(int(s['faction'],16),int(t['faction'],16));selfsame=s['index']==t['index']
  need(wp==int(p['war_relation'],16) and flag==p['war_flag49'] and war==p['named_has_war_with'] and faction==p['named_is_in_faction_with'] and selfsame==p['is_self'],'raw predicate mismatch')
  results.append({'source_tag':s['tag'],'target_tag':t['tag'],'war':war,'same_faction':faction,'candidate_only':candidate(war,selfsame),'war_pointer':hex(wp)})
 need(len(results)==7 and results[0]['war'] and results[1]['war'] and results[0]['war_pointer']==results[1]['war_pointer'],'actual bilateral war control')
 need(all(not p['war'] and not p['same_faction'] for p in results[2:]),'actual foreign nonwar/self controls')
 need(countries['3']['faction']=='0x0' and live['friendly_search_candidates']==0,'null player faction; do not enumerate empty friendly candidates')
 units=docs[BIND]['same_selected_units'];need({u['unit_id'] for u in units}=={399,481},'same selected subjects')
 for u in units:
  up=int(u['pointer'],16);need(bm.i(up+0x18)==u['handle_type']==51 and bm.i(up+0x1c)==u['unit_id'],'type51 CArmy handle not generic CId')
  need(bm.i(up+0x1e0)==u['owner_tag']==443 and bm.i(up+0x1d8)==u['intel_country_tag_1d8']==443,'fresh owner vs intel-country join')
 need(not live['promotion_eligible'] and not live['complete_relation_enum'] and not live['complete_visible_feed'],'unsupported promotion/feed claim')
 return {'pairs':results,'owner_enemy_subject_ids':[399,481],'visible_units_exported':False,'relation_exported':False,'promotion_eligible':False,'foreign_friendly_positive_count':0,'complete_visible_feed':False,'complete_input':False,'reason':'independently named war consumer proved, but actual friendly schema relation positive is missing; false-war subjects stay unknown'}
def require_promotion(result):
 need(result['promotion_eligible'] and result['foreign_friendly_positive_count']>0,'actual independently proved friendly positive required')
