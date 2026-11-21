import sys,inspect,os
sys.path.insert(0,"calling")
import gamestate
print(inspect.getsource(gamestate._rtti_name_from_vtable))
print("--- signature", inspect.signature(gamestate._rtti_name_from_vtable))
