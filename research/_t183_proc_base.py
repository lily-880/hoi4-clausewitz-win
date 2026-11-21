import sys,inspect,os
sys.path.insert(0,"calling")
from mem import Proc
print([a for a in dir(Proc) if not a.startswith("_")])
# also windows process
from process import windows
src=inspect.getsource(windows)
# too long; look for base/module
for i,line in enumerate(src.splitlines(),1):
    if "base" in line.lower() or "module" in line.lower() or "image" in line.lower():
        if i<400:
            print(f"{i}:{line}")
