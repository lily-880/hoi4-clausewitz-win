# Read-only: verify the function-pointer/literal layout at 0x2affbe8. No game mutation.
import sys,json,struct,hashlib,datetime
from pathlib import Path
Q=Path(__file__).resolve().parent;sys.path.insert(0,str(Q))
from _t207_session import Runtime
H=lambda b:hashlib.sha256(b).hexdigest()
prev=json.loads((Q/'t230_final_seal.json').read_text(encoding='utf-8'))
rt=Runtime()
try:
    g=rt.guard();assert g['pid']==10288 and g['base']=='0x7ff758fc0000' and g['pause']==1 and g['speed_slot']==0 and g['hour_tick']==60781105 and not any(g['markers'].values())
    assert rt.code(0x2795083,48).split(b'\0')[0]==b'1.19.5.0.7c6c'
    blob=rt.code(0x2affbe0,64)
    qwords=[hex(x) for x in struct.unpack('<8Q',blob)]
    # preceding COL candidate
    col=struct.unpack('<Q',rt.code(0x2affbe0,8))[0]
    col_info=None
    if rt.base<=col<rt.base+rt.pr.image_size:
        sig,off,cd,td=struct.unpack('<IIII',rt.pr.read(col,16))
        name=rt.pr.read(rt.base+td+0x10,160).split(b'\0')[0].decode('ascii','replace') if sig==1 and 0<td<rt.pr.image_size else None
        col_info={'col':hex(col),'col_rva':hex(col-rt.base),'sig':sig,'td':hex(td),'name':name}
    ascii_view=blob
    strings=[]
    i=0
    while i<len(blob):
        if 32<=blob[i]<127:
            j=i
            while j<len(blob) and 32<=blob[j]<127:j+=1
            if j-i>=4:strings.append({'off':hex(0x2affbe0+i),'text':blob[i:j].decode()})
            i=j+1
        else:
            i+=1
    after=rt.guard();assert after==g
    out={'at_est':datetime.datetime.now().astimezone().isoformat(),'before':g,'after':after,'bytes_hex':blob.hex(),'qwords':qwords,'col_at_2affbe0':col_info,'nearby_strings':strings,'function_expected':hex(rt.base+0x1eeff60),'accepted_as_vtable':False,'reason':'Pointer sits immediately before ALERT_PRIORITY loc keys; a real multi-slot vtable would overlap those strings. Class from a backward COL search is not accepted as semantic identity.'}
    (Q/'t231_priority_slot_layout.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
finally:
    rt.close()
