import sys,os,inspect
sys.path.insert(0,"calling")
os.environ["CLAUSEWITZ_ALLOW_POST"]="0"
os.environ["CLAUSEWITZ_ALLOW_WRITE"]="0"
from mem import Proc
print(inspect.getsource(Proc))
