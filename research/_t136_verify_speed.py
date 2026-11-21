import os, sys, json
sys.path.insert(0, "calling")
os.environ["CLAUSEWITZ_ALLOW_POST"] = "0"
import config, offsets as O
from mem import Proc, find_pid
from gamestate import read_campaign_summary

assert O.HYPOTHESIS_STRUCT["GS_GAME_SPEED_INDEX"] == 0x4BC
p = Proc(find_pid(config.EXE_NAME))
gs = p.u64(p.base + O.WINDOWS_GLOBALS["G_GAMESTATE"])
s = read_campaign_summary(p, gs)
fields = {k: s["fields"].get(k) for k in ("game_speed_index", "game_speed_notch", "game_speed_note", "player_tag_letter", "date_full")}
verified = {k: s["verified"].get(k) for k in ("game_speed_index", "game_speed_notch", "player_tag", "player_tag_letter", "date_full") if k in s.get("verified", {})}
print(json.dumps({"gs": hex(gs), "fields": fields, "verified_speed": verified}, ensure_ascii=False, indent=2))
p.close()
