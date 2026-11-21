import inspect,sys,os
sys.path.insert(0,"calling")
import gamestate
print(inspect.getsource(gamestate.read_campaign_summary)[:2000])
