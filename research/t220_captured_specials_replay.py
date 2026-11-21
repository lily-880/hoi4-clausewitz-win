"""t220 only: pure replay of this laptop's captured train/motor special evidence."""
import hashlib, struct
FIXED=100000
LIMIT=0x53e2d620fb40
CODE_HASHES={'0x1409890': 'b28e1f22bdf5fb7ec8563926d66bb0181bbd8f0f49c523ff5479ae14afa55b77', '0x1409810': '869b9610dbb163333f1d80eb5b6376ab2d270745d0559344600c117de09ed537', '0x7362c0': '63fed0a6a38274e9e7d910ea09b329a6000e4f9b482ac06f5653426c0c8bab11', '0xcf5620': 'd22b6b6be37dd7230fda2910e060e19edd96a80c5b63823b12ab6322a3fc2589', '0xcf5660': '8454a4e53a227554c2314fef486c3b43993f791adfd95509cd51f0abf127d2d9', '0x100f620': 'bb76a3a4b2f5a6903b0cdf3bbc5ff343b82a32a4208ab63c79a99be86e89f0eb', '0xc08790': '03ed49b5c41218f9235b80536a6ad98c1628972eb7df3219b1d43d288f274475', '0x1409630': 'e509fe659c825527e163129da7b5ed5e3d3020a12ea7f7de793a6b21bdb42a80', '0xcf2e50': 'a0c66091a5a50fff6652a96372de1cba53127bcfe66728a70b80b216be99d87a', '0x12b8e40': '7f829c8e6e8e4bc1202fb2bf460fb74b0a53941b6992545beceef7eb7c417a75', '0x12be8f0': '5294172d159eddc9934847b6fd9a89ba85422f375a8405f9c6ea4938624bb55a'}

def count(v):
 if type(v)is not int or not 0<=v<=0x7fffffff:raise ValueError('nonnegative i32 required')
 return v

def cap(v):return min(LIMIT,max(-LIMIT,v))

def special(base, stock_raw, needed, owned, train):
 count(needed);count(owned)
 if type(base)is not int or type(stock_raw)is not int or not -LIMIT<=base<=LIMIT or not -LIMIT<=stock_raw<=LIMIT:raise ValueError('scoped signed FIXED bounds')
 demand=cap(cap(base-owned*FIXED)+needed*FIXED)
 if train:demand=max(0,demand)
 current=max(0,stock_raw+(owned-needed)*FIXED) if not train else max(0,stock_raw-needed*FIXED)
 return demand,current

def replay(native, mapping, sample, join):
 for k,h in CODE_HASHES.items():
  f=native[k]['flow']
  if f['unresolved_edges'] or hashlib.sha256(bytes.fromhex(f['raw_hex'])).hexdigest()!=h:raise ValueError('native bytes/closure')
 g=sample['before']
 if g['base']!='0x7ff758fc0000' or g['pid']!=10288 or g['country_index']!=3 or any(g['markers'].values()):raise ValueError('fixture guard')
 for d in (mapping,sample,join):
  if d['before']!=g or d['after']!=g:raise ValueError('mixed/changing session')
 if mapping['stable_dependency_count']<=0 or sample['stable_dependency_count']<=0 or join['stable']<=0:raise ValueError('unstable fixture')
 if mapping['version']!='1.19.5.0.7c6c' or mapping['tag']!='SOV':raise ValueError('build/tag')
 m=mapping['map'];s=sample['mapping'];raw=g['country_index']
 if m['raw_country_tag_index']!=raw or m['country_plus8']!=raw or m['gs_ptr']!=g['gs']:raise ValueError('tag/global')
 _,capacity,n=struct.unpack('<Qii',bytes.fromhex(m['manager_array_header']))
 mapped=m['mapped_index']
 if type(mapped)is not int or not 0<=mapped<n<=capacity<=2048:raise ValueError('mapped bounds')
 if m['returned_class']!='.?AVCCountrySupplySystem@@' or m['manager_class']!='.?AVCSupplySystem@@':raise ValueError('supply RTTI')
 prefix=bytes.fromhex(m['returned_prefix_hex'])
 if struct.unpack_from('<Q',prefix,0x78)[0]!=int(g['country'],16) or struct.unpack_from('<Q',prefix,0x80)[0]!=int(m['child80_ptr'],16):raise ValueError('parent/child layout')
 if s['mapped_index']!=mapped or s['raw_country_index']!=raw or s['country_supply_ptr']!=m['returned_obj'] or s['child80_ptr']!=m['child80_ptr'] or s['country_backlink']!=g['country']:raise ValueError('mapped own object')
 for x in sample['components'].values():
  if x['count']!=0:raise ValueError('extras outside proved scope')
 c=sample['counters'];required=count(c['train_operand_child140']);owned=count(c['train_total_plus110']);worksum=0
 for row in sample['worklist_stride48']:
  b=bytes.fromhex(row['raw_hex'])
  if len(b)!=48:raise ValueError('worklist stride')
  index,number=struct.unpack_from('<ii',b)
  if (index,number,b[0x28])!=(row['country_tag_index'],row['integer_amount'],row['discriminator_28']):raise ValueError('raw worklist mismatch')
  if index!=raw or b[0x28]!=0:raise ValueError('foreign/nontrain worklist outside snapshot scope')
  worksum+=count(number)
 if worksum!=required:raise ValueError('train workload count disagreement')
 pool={}
 for row in sample['train_pool_stride24']:
  b=bytes.fromhex(row['raw_hex'])
  if len(b)!=24:raise ValueError('train pool stride')
  handle=struct.unpack_from('<Q',b)[0]
  if handle in pool:raise ValueError('duplicate variant handle')
  pool[handle]=count(struct.unpack_from('<i',b,8)[0])
  if row['handle_raw']!=handle or row['integer_amount_plus8']!=pool[handle]:raise ValueError('raw pool mismatch')
 variantptrs={v['variant_ptr']:v for v in sample['owned_train_variants']}
 if len(variantptrs)!=len(sample['owned_train_variants']):raise ValueError('duplicate variant')
 total=0;seen=set()
 for row in join['rows']:
  v=variantptrs[row['variant_ptr']];handle=row['variant_handle_plus8_raw'];qty=v['raw_quantity']
  if handle in seen or handle not in pool or type(qty)is not int or qty<0 or qty%FIXED or not v['flags_effective']&(1<<31) or v['base_name']!='train_equipment':raise ValueError('typed integral train variant')
  if qty//FIXED!=pool[handle]:raise ValueError('variant/pool count mismatch')
  total+=qty//FIXED;seen.add(handle)
 if seen!=set(pool) or len(seen)!=len(variantptrs) or total!=owned:raise ValueError('train total/handle join')
 types=sample['types'];keys={'train_equipment','motorized_equipment'}
 if set(types)!=keys:raise ValueError('scope')
 result={}
 for name,train in [('train_equipment',True),('motorized_equipment',False)]:
  t=types[name]
  if t['ptr']!=t['base_ptr'] or t['extra_flags']!=0:raise ValueError('type inheritance outside scope')
  if (t['own_flags'],t['special_44b'])!=((1<<31,0)if train else(8,1)):raise ValueError('special predicate gate')
  base=0
  for row in sample['target_requests']:
   for key in ('need','produced'):
    if not set(row[key])<=keys:raise ValueError('unexpected target')
    for v in row[key].values():
     if type(v)is not int or not 0<=v<=LIMIT:raise ValueError('request FIXED value')
   base=cap(base+row['need'].get(name,0));base=cap(base-row['produced'].get(name,0))
  need=required if train else count(c['motor_operand_c8']);own=owned if train else count(c['motor_total_plus138'])
  d,current=special(base,t['cache15_raw'],need,own,train)
  if d<0 or d%FIXED or current-d!=t['cache16_raw']:raise ValueError('fractional/negative demand or stale cache')
  result[name]={'demanded':d//FIXED,'request_base_raw':base,'native_current_raw':current,'stored_balance_raw':t['cache16_raw'],'count_operand':need,'owned_counter':own}
 return result
