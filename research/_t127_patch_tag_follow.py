from pathlib import Path

gs = Path("calling/gamestate.py")
text = gs.read_text(encoding="utf-8")
old = '''    Preference:
      1. The unique country whose observed flags at CCountry+0x538 and
         +0x53C are both 1 (exactly one such country in that session).
      2. GS+0x520 when it names a valid country, if (1) is unavailable.
'''
new = '''    Preference:
      1. GS+0x520 when it names a valid country. Live 2026-11-13: this
         followed a console `tag` switch (ETH 44 -> CHI 38) while the
         CCountry+0x538/+0x53C flags stayed on the original country.
      2. The unique country whose observed flags at +0x538 and +0x53C
         are both 1, only if (1) is unavailable. Those flags are not
         the current player after `tag`.
'''
if old not in text:
    raise SystemExit("docstring anchor not found")
text = text.replace(old, new, 1)

old2 = '''    if len(hits) == 1:
        idx = hits[0]
        out["player_index"] = idx
        out["ok"] = True
        if valid_520 and cand_520 == idx:
            out["source"] = "human_flags+gs_0x520"
        else:
            out["source"] = "human_flags"
            if valid_520 and cand_520 != idx:
                out["disagreement_gs_0x520"] = cand_520
    elif valid_520:
        out["player_index"] = cand_520
        out["ok"] = True
        out["source"] = "gs_0x520"
        out["reason"] = "human flags not unique; used observed GS+0x520"
    else:
        out["reason"] = "no unique human-player flag and GS+0x520 not a valid country"
        return out
'''
new2 = '''    if len(hits) == 1:
        out["original_human_index"] = hits[0]
    if valid_520:
        out["player_index"] = cand_520
        out["ok"] = True
        if len(hits) == 1 and hits[0] == cand_520:
            out["source"] = "gs_0x520+human_flags"
        else:
            out["source"] = "gs_0x520"
            if len(hits) == 1 and hits[0] != cand_520:
                # Flags still name the country selected at game start;
                # they do not follow console `tag`.
                out["human_flags_unmoved"] = hits[0]
    elif len(hits) == 1:
        out["player_index"] = hits[0]
        out["ok"] = True
        out["source"] = "human_flags"
        out["reason"] = "GS+0x520 not a valid country; fell back to human flags"
    else:
        out["reason"] = "GS+0x520 not a valid country and no unique human-player flag"
        return out
'''
if old2 not in text:
    raise SystemExit("decision anchor not found")
text = text.replace(old2, new2, 1)
gs.write_text(text, encoding="utf-8")

off = Path("calling/offsets.py")
ot = off.read_text(encoding="utf-8")
old3 = '''    # Observed live 2026-11-13 on the same process: i32 country index at
    # GS+0x520 equaled the human player (44). Class field name not proven.
    "GS_PLAYER_INDEX_OBSERVED": 0x520,
'''
new3 = '''    # Observed live 2026-11-13: i32 country index of the country the
    # player currently controls. Follows console `tag` (ETH 44 -> CHI 38
    # in that session). Class field name not proven.
    "GS_PLAYER_INDEX_OBSERVED": 0x520,
'''
if old3 not in ot:
    raise SystemExit("offsets 0x520 comment not found")
ot = ot.replace(old3, new3, 1)
old4 = '''    # Observed live 2026-11-13: i32 at +0x538 and +0x53C were 1 only for
    # the human-controlled country (index 44) among 440 CCountry objects.
    # Class field names not RTTI-proven; treat as human-player flags only.
'''
new4 = '''    # Observed live 2026-11-13: i32 at +0x538 and +0x53C were 1 only for
    # the originally selected human country (ETH 44) among 440 CCountry
    # objects. They did not follow a later console `tag` to CHI 38.
    # Class field names not RTTI-proven; not the current player after tag.
'''
if old4 not in ot:
    raise SystemExit("offsets flag comment not found")
ot = ot.replace(old4, new4, 1)
off.write_text(ot, encoding="utf-8")

import py_compile
py_compile.compile("calling/offsets.py", doraise=True)
py_compile.compile("calling/gamestate.py", doraise=True)
print("patched ok")
