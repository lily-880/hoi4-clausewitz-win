import inspect, sys
sys.path.insert(0, "calling")
import mem
from mem import find_pid as mem_find
print("mem.find_pid", mem_find("hoi4.exe"), mem_find)
print(inspect.getsource(mem_find))
try:
    import process
    print("process.find_pid", process.find_pid())
    print(inspect.getsource(process.find_pid))
except Exception as e:
    print("process import/find err", e)
