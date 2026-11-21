# -*- coding: utf-8 -*-
import hashlib, json, re
from pathlib import Path

INV = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
text = INV.read_text(encoding="utf-8")
old = text
text = text.replace(
    "| meta.speed | 未验证 | 当前暂停或1x状态，暂停标志尚未证明。 |",
    "| meta.speed | 已验证 | 官方暂停标志为 CInGameIdler+0x6c1（CPauseGame 经 idler 虚函数 +0x2f0 读取，+0x298 写入）。当前为暂停。GS+0x4B8 小时进度与 +0x4BC 速度档不是暂停标志。 |",
)
assert text != old
rows = [ln for ln in text.splitlines() if re.match(r"^\| [^|]+ \| (已验证|未验证) \|", ln)]
ver = sum(1 for ln in rows if "| 已验证 |" in ln)
unver = sum(1 for ln in rows if "| 未验证 |" in ln)
tables = sum(1 for ln in text.splitlines() if ln.startswith("| 字段名 |"))
assert len(rows)==116 and ver==47 and unver==69 and tables==14, (len(rows),ver,unver,tables)
INV.write_text(text, encoding="utf-8", newline="\n")
sha = hashlib.sha256(INV.read_bytes()).hexdigest()
print("D sha", sha, "47/69")

# freeze t186 live SHA pin
p = Path("research/test_t186_input_wars.py")
t = p.read_text(encoding="utf-8")
old = """        raw = INV.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(sha, T186_SHA)
        rec = json.loads((ROOT / "research/t186_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["sha256"], T186_SHA)
"""
new = """        rec = json.loads((ROOT / "research/t186_inventory_sha256.json").read_text(encoding="utf-8"))
        self.assertTrue(rec["updated"])
        self.assertEqual(rec["sha256"], T186_SHA)
        raw = INV.read_bytes()
        # live D SHA may change in later batches; this test pins t186's recorded hash
"""
assert old in t
p.write_text(t.replace(old, new), encoding="utf-8", newline="\n")
print("frozen t186 inventory sha pin")

Path("research/t187_inventory_sha256.json").write_text(json.dumps({
    "path": str(INV),
    "sha256": sha,
    "updated": True,
    "fields": 116,
    "verified": 47,
    "unverified": 69,
    "tables": 14,
    "columns": 3,
    "header": "| 字段名 | 已验证/未验证 | 说明 |",
    "promoted": ["meta.speed"],
    "previous_sha256": "2bf707a0a097487bb6e17797ab6cde12e6dcaf9203c90a3f984c222474299d62",
    "complete_input": False,
}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

proof = {
    "promoted": ["meta.speed"],
    "live_value": "pause",
    "official": {
        "CPauseGame": {
            "rtti": ".?AVCPauseGame@@",
            "vtable": "0x29e6e10",
            "command_token": "0x29ec pausegame (getter 0xe56c30)",
            "execute": "0xe55060 (vtable +0x50)",
            "execute_calls": "G_IDLER (0x33ddb08) CInGameIdler vt+0x2f0 then vt+0x298 with edx=command+0x48",
        },
        "CInGameIdler": {
            "getter_vt_plus_0x2f0": "0xe46300  movzx eax, byte [rcx+0x6c1]; ret",
            "setter_vt_plus_0x298": "0xe487f0",
            "pause_flag": "byte +0x6c1",
            "related": "+0x6c0 cleared at setter entry; +0x6c3 is a sibling flag written with +0x6c1 on the force-pause path, not the official query",
        },
        "not_game_pause": {
            "token_paused_0x3691": "national-focus writer 0x2f52a0 (activate_shine_on_focus / completed / progress)",
            "unit_controller_pause_0x35ba": "CArmy secondary writer 0xced2e0, unit-level",
            "GS_plus_0x4B8": "hour progress f32, ticks only while unpaused; not the pause flag",
            "GS_plus_0x4BC": "speed index (0=1x setting); live 0 while paused",
        },
    },
    "live": json.loads(Path("research/t187_live_pause.json").read_text(encoding="utf-8")),
    "clips": [
        "research/_t187_clip_Pause_0xe55060.txt",
        "research/_t187_clip_Pause_0xe56c30.txt",
        "research/_t187_clip_idler_query_vt2f0_0xe46300.txt",
        "research/_t187_clip_idler_setpause_0xe487f0.txt",
    ],
    "schema": "meta.speed enum pause|1x; this snapshot is pause",
}
Path("research/t187_pause_flag.json").write_text(json.dumps(proof, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

off_path = Path("calling/tables/offsets_input_windows_1.19.5.json")
off = json.loads(off_path.read_text(encoding="utf-8"))
off["pause_flag_t187"] = {
    "CInGameIdler_pause_flag": "+0x6c1",
    "getter": "vtable +0x2f0 = 0xe46300",
    "setter": "vtable +0x298 = 0xe487f0",
    "CPauseGame_execute": "0xe55060",
    "G_IDLER": "0x33ddb08",
    "live": "1 (pause)",
    "not_pause": ["GS+0x4B8 hour progress", "GS+0x4BC speed index", "token paused 0x3691 focus", "unit_controller_pause"],
    "promoted": ["meta.speed"],
    "proofs": ["research/t187_pause_flag.json", "research/t187_live_pause.json"],
}
off_path.write_text(json.dumps(off, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("proofs ok")
