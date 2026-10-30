# AUTO Phase 2cw — load JSON sidecar into LAND_POST_READINESS
from pathlib import Path as _P
import json as _json
_side = _P(__file__).with_name('_land_post_2cw.json')
if _side.exists():
    _blob = _json.loads(_side.read_text(encoding='utf-8'))
    for _k, _v in _blob.items():
        LAND_POST_READINESS[_k] = _v
