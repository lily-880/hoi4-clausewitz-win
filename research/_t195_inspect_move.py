import inspect, sys
from pathlib import Path
ROOT = Path(r"C:\Users\Lenovo\Documents\Paradox Interactive\Hearts of Iron IV\clausewitz_win")
sys.path.insert(0, str(ROOT / "calling"))
import move_order as mo
print("FILE", mo.__file__)
for name, obj in inspect.getmembers(mo):
    if name.startswith("_"):
        continue
    if inspect.isfunction(obj) or inspect.isclass(obj):
        try:
            sig = str(inspect.signature(obj))
        except Exception:
            sig = ""
        print(name, sig)
# also constants
for name in dir(mo):
    if name.isupper() or "FACTORY" in name or "RVA" in name or "VT" in name or "ISVALID" in name:
        print("CONST", name, "=", getattr(mo, name))
