# Offline analysis of current guarded raw bytes; never calls the native function.
import json,struct,hashlib
from pathlib import Path
Q=Path(__file__).resolve().parent
D=json.loads((Q/'t238_alert_visibility_filter.json').read_text(encoding='utf-8'));F=D['functions']['0xb620c0'];RAW=bytes.fromhex(F['raw_hex']);BASE=int(F['window_start'],16)
assert hashlib.sha256(RAW).hexdigest()==F['sha256']
TARGETS=struct.unpack_from('<2I',RAW,0xb620ec-BASE);LUT=RAW[0xb620f4-BASE:0xb620f4-BASE+74]
assert TARGETS==(0xb620e6,0xb620e9) and len(LUT)==74 and set(LUT)=={0,1}
assert RAW[0xb620e6-BASE:0xb620e6-BASE+3]==b'\xb0\x01\xc3'
assert RAW[0xb620e9-BASE:0xb620e9-BASE+3]==b'\x32\xc0\xc3'
def classify(alert_id):
 if type(alert_id) is not int or not 0<=alert_id<2**32:raise ValueError('exact native u32 alert ID required')
 index=(alert_id-8)&0xffffffff
 return index<=0x49 and TARGETS[LUT[index]]==0xb620e6
if __name__=='__main__':
 out=dict(source_raw_sha256=F['sha256'],jump_table_rva='0xb620ec',lookup_rva='0xb620f4',lookup_count=74,case_targets=[hex(x) for x in TARGETS],true_ids=[i for i in range(82) if classify(i)],false_ids_in_0_81=[i for i in range(82) if not classify(i)],receiver_consumed=False,heap_reads=0,output='AL constant0or1 selected solely byEDX u32 alertID',branch_closure='Original walk reports indirect jump; complete case set independently resolved from bounded raw jump/LUT tables and exact constant-return case bytes. No other destinations.',native_invocations=0,genuine_schema_severity_positive_samples=0,genuine_schema_severity_negative_samples=0,scope='Static alert-ID partition used by caller UI layout branch, NOT aggregate priority or per-entry severity. Provisional visibility_filter filename does not establish visibility semantics.')
 (Q/'t238_static_id_partition_proof.json').write_text(json.dumps(out,indent=2)+'\n');print('resolved',len(out['true_ids']),'true IDs; false',out['false_ids_in_0_81'],'schema controls0/0')
