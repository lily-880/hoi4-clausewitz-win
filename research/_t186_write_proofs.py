# -*- coding: utf-8 -*-
import json, hashlib
from pathlib import Path

SHA = "2bf707a0a097487bb6e17797ab6cde12e6dcaf9203c90a3f984c222474299d62"
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
live = hashlib.sha256(inv.read_bytes()).hexdigest()
assert live == SHA, (live, SHA)

writers = {
    "promoted": ["world.wars.a", "world.wars.b", "world.wars.state"],
    "not_promoted": ["world.wars.front_invalidated"],
    "CRelation": {
        "rtti": ".?AVCRelation@@",
        "vtable": "0x29dcb48",
        "writer": "0xd8f520",
        "first": "country index at +0x10, token 0x28de, via 0xc08170",
        "second": "country index at +0x14, token 0x28df, via 0xc08170",
        "cancel": "byte +0x48 token 0x28e5, written iff nonzero",
        "start_date": "CGameDate secondary at +0x28 (primary at +0x18, hour tick at +0x20) token 0x28e0, written when cancel==0",
        "end_date": "CGameDate at +0x40, token 0x28e1, written iff dword[+0x38] > dword[+0x20]",
        "start_date_live_note": "live tick at +0x20 equals current campaign hour 60759371 (1936-01-01 12); historical outbreak date is not proven on this snapshot",
    },
    "CWarRelation": {
        "rtti": ".?AVCWarRelation@@",
        "vtable": "0x29dcc08",
        "writer": "0xd8f900 (calls 0xd8f520 first)",
        "first_was_instigator": "byte +0x158 token 0x3af7",
        "hostility_reason_instigator": "dword +0x160 token 0x381d; 0=war 1=puppet 2=ally 3=asked_to_join 4=guarantee 5=not_applicable",
        "hostility_reason_defender": "dword +0x15c token 0x381e, same enum",
        "plus_0x49": "official getters 0xd82c10 / 0xd7e050 skip the war if byte +0x49 is nonzero",
    },
    "CRelationStatus": {
        "war_relation_slot": "+0x2e8 CWarRelation*",
        "official_getters": ["0xd7db8b", "0xd7deb0", "0xd7da30"],
        "note": "GetWarRelation: resolve first country +0xf88 CDiplomacyStatus, index second in active_relations, return [status+0x2e8]",
    },
    "CDiplomacyStatus": {
        "rtti": ".?AVCDiplomacyStatus@@",
        "country_offset": "CCountry+0xf88",
        "writer": "0xdad1a0",
        "active_relations": "token 0x2e43, data +0x8, size +0x14, 440 CRelationStatus* (index 0 is the null slot; index is country index)",
        "capitulated": "byte +0x328 token 0x3549, country-level, not proven as War.state",
    },
    "clips": [
        "research/_t186_clip_warrelation_writer_0xd8f900.txt",
        "research/_t186_clip_relation_base_0xd8f520.txt",
        "research/_t186_clip_diplomacystatus_writer_0xdad1a0.txt",
        "research/_t186_clip_getter_0xd7db8b.txt",
        "research/_t186_clip_use_0xd82c10.txt",
    ],
}
Path("research/t186_war_writers.json").write_text(json.dumps(writers, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

contract = {
    "schema": "War requires a, b (CountryRef index, optional tag) and state enum at_war|ceasefire|capitulated|puppeted|not_at_war; front_invalidated optional",
    "mapping": {
        "a": "CWarRelation.first +0x10 -> CountryRef",
        "b": "CWarRelation.second +0x14 -> CountryRef",
        "state": "at_war when a CWarRelation is present at both sides' CRelationStatus+0x2e8, cancel==0, byte +0x49==0, and official end_date key is omitted; other enum values not proven",
        "front_invalidated": "no named token; not promoted",
    },
    "live": {
        "unique_world_wars": 1,
        "first": {"index": 16, "tag": "ITA"},
        "second": {"index": 44, "tag": "ETH"},
        "state": "at_war",
        "cancel": 0,
        "plus_0x49": 0,
        "first_was_instigator": 1,
        "hostility_reasons": 0,
        "shared_object": "0x26c70b635d0",
        "pairs": [["ITA", "ETH"], ["ETH", "ITA"]],
        "player_visible": "player ETH is second; this is the only war in the world snapshot; not a fog-hidden third-party war",
    },
    "do_not_invent_from_diplomacy_status_alone": True,
    "do_not_map_hostility_reason_to_state": True,
    "do_not_map_country_capitulated_byte_to_war_state": True,
}
Path("research/t186_war_contract.json").write_text(json.dumps(contract, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

off_path = Path("calling/tables/offsets_input_windows_1.19.5.json")
off = json.loads(off_path.read_text(encoding="utf-8"))
off["war_relation_t186"] = {
    "CWarRelation_writer": "0xd8f900",
    "CRelation_writer": "0xd8f520",
    "first": "+0x10 country index",
    "second": "+0x14 country index",
    "cancel": "byte +0x48",
    "end_date_gate": "[+0x38] > [+0x20]",
    "CRelationStatus_war_slot": "+0x2e8",
    "CDiplomacyStatus": "CCountry+0xf88; active_relations +0x8/+0x14",
    "live": "one world war first=ITA/16 second=ETH/44 state=at_war",
    "promoted": ["world.wars.a", "world.wars.b", "world.wars.state"],
    "promoted_front_invalidated": False,
    "proofs": [
        "research/t186_war_writers.json",
        "research/t186_war_contract.json",
        "research/t186_live_warrelation.json",
        "research/t186_world_warrelations.json",
    ],
}
off_path.write_text(json.dumps(off, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
print("offsets ok", "sha confirmed", live)
