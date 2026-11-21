import sys
sys.path.insert(0,"calling")
from pe import PE
pe=PE(r"D:\STEAM\steam\steamapps\common\Hearts of Iron IV\hoi4.exe")
s=pe.sections[0]
print(type(s), dir(s))
print(s)
