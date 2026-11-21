"""t221 only: pure replay of official signed remainder and deficit-disproof evidence."""
import hashlib
FIXED = 100000
SCOPE = ("infantry_equipment", "artillery_equipment", "support_equipment",
         "light_tank_chassis", "motorized_equipment", "train_equipment")
DEMANDED = {"infantry_equipment": 10015, "artillery_equipment": 147, "support_equipment": 121,
            "light_tank_chassis": 2324, "motorized_equipment": 1278, "train_equipment": 0}
TRAIN_TOTAL, TRAIN_COMMITMENT, TRAIN_REMAINDER = 83, 15, 6800000
CODE_HASHES = {'0x1e1f6a0': '4fef33d7938fbd29da306bf646b62738b598561e00c4a16c1afb2156bd88cb8f', '0x1e208f0': '9b7f73b41ab0d19e0a4b5a5e048d1d574ea77aa8e93e090edb1bbc2012a5712f', '0x1e1a680': '05f7f277cbb0e30df991a11ce99c21c08c2a0354f0dfff54456cc1d3ed1a80df', '0x1409700': 'ef5de1387dc008e3576f9bebcecc104461604135dd9d45504636025eaa67054c', '0x14076d0': 'f2e45d5ee501567cffb70575ce04d1e70b6411546c43746024d40d8d46d0a514'}
SITES = {"equipment_type": "1e1f98b", "in_stock": "1e1fcaa", "needs": "1e1fe01",
         "produced": "1e1ff9e", "balance": "1e20158"}

def _flow(doc, addr):
    return doc["flows"][addr] if "flows" in doc and addr in doc.get("flows", {}) else doc["flow"]

def _join(asm):
    return "\n".join(asm)

def replay(ui, generic, fmt, cur, train):
    docs = {"0x1e1f6a0": ui, "0x1e208f0": ui, "0x1e1a680": fmt, "0x14076d0": generic, "0x1409700": cur}
    for addr, expected in CODE_HASHES.items():
        f = _flow(docs[addr], addr)
        if f["unresolved_edges"] or hashlib.sha256(bytes.fromhex(f["raw_hex"])).hexdigest() != expected:
            raise ValueError("native bytes/closure")
    g = cur["before"]
    if g["pid"] != 10288 or g["base"] != "0x7ff758fc0000" or g["country_index"] != 3 or any(g["markers"].values()):
        raise ValueError("fixture guard")
    if cur["after"] != g or train["after"]["hour_tick"] != g["hour_tick"] or train["before"]["pid"] != 10288:
        raise ValueError("mixed/changing session")
    if ui["before"] != g or generic["before"] != g or fmt["before"] != g:
        raise ValueError("mixed-session code capture")
    if cur["stable"] <= 0 or cur["countryresources"]["count77c"] != 0 or cur["countryresources"]["count764"] != 0:
        raise ValueError("unstable or nonempty 1409700/14080c0 extras")
    if cur["countryresources"]["header770_hex"] != "00000000000000000000000000000000":
        raise ValueError("nonempty 1409700 header")
    row = ui["flows"]["0x1e1f6a0"]["asm"]
    text = _join(row)
    for tok, site in SITES.items():
        if not any(line.startswith(site + " lea rdx") for line in row):
            raise ValueError("missing official token " + tok)
    lowered = text.lower()
    if "deficit" in lowered or "shortage" in lowered or "缺口" in text:
        raise ValueError("unexpected deficit-named token")
    if "mov qword ptr [r15 + 0x5f8], rax" not in text or "sub qword ptr [r15 + 0x5f8], r8" not in text:
        raise ValueError("missing official remainder store/subtract")
    if "mov qword ptr [r15 + 0x648], r8" not in text or text.count("0x648") != 1:
        raise ValueError("official need is only a hidden subtrahend here")
    instock = _join(x for x in row if "1e1fcaa" <= x.split()[0] <= "1e1fe00")
    bal = _join(x for x in row if "1e20158" <= x.split()[0] <= "1e20260")
    if "mov rbx, qword ptr [r15 + 0x5f8]" not in instock or "lea r9, [r15 + 0x5f8]" not in instock:
        raise ValueError("in_stock is not the signed remainder field")
    if "mov rbx, qword ptr [r15 + 0x608]" not in bal or "lea r9, [r15 + 0x608]" not in bal:
        raise ValueError("balance token is not the 14076d0 residual")
    if "0x5f8" in bal or "0x648" in instock:
        raise ValueError("token/field crossing")
    fmtasm = _join(fmt["flows"]["0x1e1a680"]["asm"])
    if "cmp byte ptr [rbp + 0x7f], r13b" not in fmtasm or "jne 0x1e1a8ef" not in fmtasm or "1e1a8ef cmp rbx, r9" not in fmtasm:
        raise ValueError("missing signed formatter flag path")
    if "movsxd rsi, dword ptr [r14 + 0x77c]" not in _join(cur["flow"]["asm"]):
        raise ValueError("1409700 array bind")
    c = train["counters"]
    if (c["train_total_plus110"], c["train_operand_child140"]) != (TRAIN_TOTAL, TRAIN_COMMITMENT):
        raise ValueError("frozen train counters changed")
    if train["types"]["train_equipment"]["cache15_raw"] != 8300000 or train["types"]["train_equipment"]["cache16_raw"] != TRAIN_REMAINDER:
        raise ValueError("frozen train caches changed")
    result = {}
    for name in SCOPE:
        slot = cur["six_type_slot_values"][name]
        rem = slot["cache16"]
        if type(rem) is not int:
            raise ValueError("non-integer remainder")
        # Independent stored official remainder must match the earlier train/motor cache snapshot.
        if name in train["types"] and rem != train["types"][name]["cache16_raw"]:
            raise ValueError("stale or crossed type remainder")
        short = max(0, -rem)
        if short % FIXED:
            raise ValueError("fractional shortfall")
        if short // FIXED != DEMANDED[name]:
            raise ValueError("shortfall is not official demanded, or surplus misclassified")
        result[name] = {"signed_remainder_raw": rem, "nonnegative_shortfall": short // FIXED, "demanded": DEMANDED[name],
                        "cache15_raw": slot["cache15"]}
    tr = result["train_equipment"]
    if tr["signed_remainder_raw"] != TRAIN_REMAINDER or tr["nonnegative_shortfall"] != 0 or tr["cache15_raw"] != 8300000:
        raise ValueError("train remainder must be uncommitted 68, not total 83 or commitment 15")
    return result
