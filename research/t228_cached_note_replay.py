"""Frozen t228 cache-only supplementary-note evidence. No IO/backend/game integration.
Group advisory text stays group-scoped; associated IDs remain sampled causal witness only.
"""
import hashlib,re,struct
from t227_qualified_crisis_replay import Frozen,Unproved,need,supply
BASE=0x7ff758fc0000
PINS={'0xb79d00': '2945c5fbc9fbcd3966ac0d44f5bd6385fae3634cb5f1d7f82b9c7a650ce9360d', '0xb61660': 'fa074eabd55136dc181c366991c6747d07b6ac1bd994c743688050ee2eaab577', '0xb50ab0': 'eac9d4a813627453b0005929c55317000e3b8a2df34fee540fa67c2a61793ad5', '0xb54c00': 'c17cb6c5ef73bd9406ba7deab730a1a97bf60b8ba5947c7dfc44974843138bbe', '0xb52a30': '98bacb76adc62a1a3b9c1c64de5db3e4b039e32400fbc18e9e0549ab01831dfd', '0xb525a0': 'fb6da78ff95422d84beefdaa27bf855903b307092f0146623df09d1fe1a5905e', '0x65e780': '3655abe9b5ef10aa85086cad8b1b631a7e72438baab3e756a135ab3c4020bbff'}
def body_text(text):
 need(isinstance(text,str) and bool(text),'empty cached note')
 need(not re.fullmatch(r'(?:[A-Z][A-Z0-9_]+|alert_[a-z0-9_]+)',text),'localization key is not note')
 need(not re.search(r'\$[^$\n]+\$|\[[^\]\n]*\.(?:Get|Has|Is)[^\]\n]*\]|\{(?:\d+|[A-Za-z_]\w*)\}',text),'unexpanded placeholder')
 need(all(c.isprintable() or c in '\t\n\r\x11' for c in text),'unknown text control')
 return text

def raw_text(f,a,meta):
 b=f.read(a,32);n,c=struct.unpack_from('<QQ',b,16);need(0<=n<=4096 and n<=c<=1048576,'string byte length/capacity')
 raw=b[:n] if c<=15 else f.read(struct.unpack_from('<Q',b)[0],n)
 try:text=raw.decode('utf-8')
 except UnicodeError:raise Unproved('cached UTF-8')
 need(meta['length']==n and meta['capacity']==c and meta['raw_hex']==raw.hex() and meta['text']==text,'raw cached metadata')
 need('address' not in meta or meta['address']==hex(a),'cached string provenance')
 return text

def replay(probe,scope,chain):
 for d in (probe,scope):
  g=d['before'];need(g==d['after'],'unstable guard');need(g['pid']==10288 and g['base']==hex(BASE) and g['country_index']==3 and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values()),'session gate')
 need(probe['before']==scope['before'],'mixed bindings')
 fs=chain['functions']
 for a,h in PINS.items():
  need(a in fs,'missing independent native producer');f=fs[a];need(not f['unresolved_edges'] and not f['external_tails'],'open native text proof');need(f['sha256']==h and hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()==h,'native text integrity')
 def ops(a,*expected):
  actual=[s.partition(' ')[2] for s in fs[a]['asm']];need(all(x in actual for x in expected),'native text semantics')
 ops('0xb50ab0','mov edx, 4','call 0xb61660')
 ops('0xb61660','movabs rax, 0x646579616c65645f','add rcx, 0x28','call 0x22aeab0','call 0x1216a0')
 ops('0xb79d00','lea rdx, [r13 + 0x410]','call 0x11f770','movabs r10, 0x646579616c65645f','lea rsi, [r13 + 0x28]','lea rcx, [r13 + 0x28]','call 0x22aeab0','call 0x12b330','cmp qword ptr [rax + 8], r14','cmp qword ptr [rax], 0','cmp qword ptr [rax + 0x18], 0')
 ops('0xb54c00','lea rcx, [rsp + 0x30]','call 0xb52a30','mov qword ptr [rbp + 0x370], rbx')
 ops('0xb52a30','add rcx, 8','add rdx, 8','call 0xb525a0')
 ops('0xb525a0','lea rcx, [rdi + 0x20]','lea rdx, [rbx + 0x20]','call 0x11f770')
 ops('0x65e780','movups xmm0, xmmword ptr [rdx + 0x20]','movups xmmword ptr [rcx + 0x20], xmm0')
 for va,key in [('0x29c5118','LOW_SUPPLIES_TIPS'),('0x29c4210','ALERT_RIGHTCLICK')]:
  v=scope['literals'][va];need(bytes.fromhex(v['raw_hex']).split(b'\0')[0].decode()==key==v['ascii_prefix'],'named cached advice producer')
 sm=Frozen(scope);country=int(scope['before']['country'],16);tp=int(scope['theatre'],16);tg=int(scope['theater_group'],16);og=int(scope['orders_group'],16)
 need(tp in sm.array(country+0x168,64) and tg in sm.array(tp+0xc8,128) and og in sm.array(tg+0x48,128),'native group membership')
 members=sm.array(og+0x50,256);need(len(members)==scope['member_count']==25 and scope['sample_count']==len(scope['controls'])==3,'three-of25 scope')
 hours=sm.i(BASE+0x33e3678);threshold=sm.sq(BASE+0x33e3e00);need(hours==scope['hours']==72 and threshold==scope['out_threshold']==99000,'supply predicate globals');by={}
 for mp,row in zip(members,scope['controls']):
  u=mp-0xb8;need(sm.q(sm.q(mp)+0x20)==BASE+0xc4f050 and sm.q(sm.q(u)+0x40)==BASE+0x20f350,'member virtual adjustments')
  need(sm.i(u+0x18)==51 and sm.i(u+0x1e0)==3 and sm.q(u+0xc0)==og,'type51 owner membership');uid=sm.i(u+0x1c);pp=sm.q(u+0x1f0);pid=sm.i(u+0x28);need(sm.i(pp+0xa4)==pid,'province join')
  source=sm.sq(u+0x40);cap=sm.sq(u+0x600);reserve=sm.sq(u+0x610);special=bool(sm.q(u+0x2f8));eff,out,bucket=supply(source,cap,reserve,hours,threshold,special)
  need((uid,pid,source,eff,cap,reserve,special,out,bucket)==tuple(row[k] for k in ('unit_id','province_id','source_raw','effective_raw','capacity_raw','reserve_raw','special','out_of_supply','native_bucket')),'raw witness controls');by[uid]=(pid,out,bucket)
 need(set(by)=={500,374,479} and by[479]==(1780,True,0) and by[374]==(1790,False,2),'causal positive negative')
 need(len(scope['selected'])==1,'ambiguous scoped note');sel=scope['selected'][0]
 pm=Frozen(probe);idler=int(probe['before']['idler'],16);manager=pm.q(idler+0x7a8);need(sm.q(idler+0x7a8)==manager,'fresh manager equality');need(probe['current_theater_group']==hex(tg),'same current group')
 rows={r['alert_id']:r for r in probe['rows']};need(set(rows)=={3,4},'actual alert pair')
 for aid,row in rows.items():
  master=manager+aid*0x468;need(row['master']==hex(master),'master provenance');name=raw_text(pm,master+0x410,row['master_name']);need(name==('alert_low_supply' if aid==3 else 'alert_very_low_supply'),'master names')
  raw_text(pm,master+8,row['master_instant']);raw_text(pm,master+0x28,row['master_delayed'])
  ptr,c,n=struct.unpack('<QII',pm.read(manager+(aid+0xf0e)*24,16));need(0<=n<=c<=32 and n==row['active_count']==len(row['entries']),'active header')
  need(n==(0 if aid==3 else 1),'actual active4 not master fallback')
 entry=rows[4]['entries'][0];ptr,c,n=struct.unpack('<QII',pm.read(manager+(4+0xf0e)*24,16));ep=ptr;need(entry['entry']==sel['entry']==hex(ep),'same active entry')
 for f in (pm,sm):
  p,c,n=struct.unpack('<QII',f.read(manager+(4+0xf0e)*24,16));need(p==ep and n==1 and n<=c<=32,'same active header');k=struct.unpack('<QQQQ',f.read(ep+0x438,32));need((k[0],k[1],k[3])==(0,tg,0),'active context keys')
 need((entry['key0'],entry['group'],entry['key3'],entry['same_current_group'])==('0x0',hex(tg),'0x0',True),'declared active context')
 need(raw_text(pm,ep+0x410,entry['name'])==raw_text(sm,ep+0x410,sel['name'])=='alert_very_low_supply','actual active name')
 instant=raw_text(pm,ep+8,entry['instant']);need(instant==raw_text(sm,ep+8,sel['instant']),'stable title')
 text=raw_text(pm,ep+0x28,entry['delayed']);need(text==raw_text(sm,ep+0x28,sel['delayed']),'stable actual text');body_text(text)
 need(text!=instant and text!=rows[4]['master_delayed']['text'],'active extended advice not title/template')
 return {'qualified_fields':{'kind':'out_of_supply','unit_ids':[479],'province_ids':[1780],'notes':text},'note_scope':'same native group cached advisory; not unit479-specific diagnosis or complete affected-unit census','sampled_members':3,'native_member_count':25,'note_byte_length':len(text.encode('utf-8')),'note_raw_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),'raw_rich_text_preserved':True,'native_formatters_invoked':False,'kind_is_composed_not_native_enum':True,'severity_exported':False,'complete_crisis_record':False,'complete_crisis_feed':False,'complete_input':False,'registration_parameter_5_is_not_schema_severity':True}
