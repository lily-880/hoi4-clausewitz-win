"""t219 captured-host-only arithmetic replay; no process backend, CLI or exporter."""
import hashlib
SCOPE = ("artillery_equipment", "infantry_equipment", "support_equipment", "light_tank_chassis")
FIXED = 100000
MAXIMUM = 0x53e2d620fb40
CONTRACT = {'0x1409810': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': '869b9610dbb163333f1d80eb5b6376ab2d270745d0559344600c117de09ed537', 'tails': []}, '0x1409890': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': 'b28e1f22bdf5fb7ec8563926d66bb0181bbd8f0f49c523ff5479ae14afa55b77', 'tails': []}, '0x100f620': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': 'bb76a3a4b2f5a6903b0cdf3bbc5ff343b82a32a4208ab63c79a99be86e89f0eb', 'tails': []}, '0xcf5620': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': 'd22b6b6be37dd7230fda2910e060e19edd96a80c5b63823b12ab6322a3fc2589', 'tails': []}, '0xcf5660': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': '8454a4e53a227554c2314fef486c3b43993f791adfd95509cd51f0abf127d2d9', 'tails': []}, '0x7362c0': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': '63fed0a6a38274e9e7d910ea09b329a6000e4f9b482ac06f5653426c0c8bab11', 'tails': []}, '0x140ba10': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': 'dd34f1ff710f16d296d2c81e729407c4142cdecc4b3ec1f8137ad9be99a3d021', 'tails': []}, '0x15b1d90': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': '088a3b41d8a5a518fd43b75a36d9712e03952644cc84aecff480ef14aa5f13ac', 'tails': []}, '0x15b3220': {'file': 't219_equipment_type_and_cache_flows.json', 'sha256': '5cc1ae16a742b454b32c920405a492c1f471327fcec66fe1a98da3f1240c7baa', 'tails': []}, '0x140a400': {'file': 't219_cache_reader_and_component_flows.json', 'sha256': '5327aa42e1bb77f1e9f22c1cd50d1f028d73df2d04f60d07f601f84351e360f2', 'tails': []}, '0x1409e50': {'file': 't219_cache_reader_and_component_flows.json', 'sha256': '1dc6a01ddc3b5cbd1c496f0561dc9828eaefe70a916a700dc5e558f8fb2dcf3c', 'tails': []}, '0x140a600': {'file': 't219_cache_reader_and_component_flows.json', 'sha256': '555589b07dce1e4c3b8873199ac3d579e20a8b96bc20ca47e5a34da1bd2a8000', 'tails': []}, '0x14080c0': {'file': 't219_cache_reader_and_component_flows.json', 'sha256': '3d784d40ac4362bbfafab0072eba410111e61339f663dd9ab4b5617f6ea1ebb6', 'tails': []}, '0x1407e60': {'file': 't219_cache_reader_closed_windows.json', 'sha256': '08414d9af3d0dcb42af0f41698b9cd42d44dfcb2b35066d4b133a288c6319383', 'tails': []}, '0xc08790': {'file': 't219_cache_reader_closed_windows.json', 'sha256': '03ed49b5c41218f9235b80536a6ad98c1628972eb7df3219b1d43d288f274475', 'tails': []}, '0x717360': {'file': 't219_cache_reader_closed_windows.json', 'sha256': '857ea8150416da5c87146300bc1c48110a7e326b4a5e12239f04166fc2d9bdfa', 'tails': []}, '0xcf2e70': {'file': 't219_scoped_demand_leaf_controls.json', 'sha256': '73292b2b2e753c0c184a6f14c8249270a51136ecc191cd64c67fdad0f6b705e5', 'tails': [{'site': '0xcf2e97', 'target': '0x100f620'}]}, '0x15b2ab0': {'file': 't219_scoped_demand_leaf_controls.json', 'sha256': '9d7218b8718bbe66488b2044edd8e3763de26a5b3be773097525b561ac4b276b', 'tails': []}, '0xb2cb40': {'file': 't219_scoped_demand_leaf_controls.json', 'sha256': '614c291c78d1882dada0afe3f0bb9bc2deb44cde645177552f75c20d9b000011', 'tails': []}, '0x717400': {'file': 't219_scoped_demand_leaf_controls.json', 'sha256': '41b41d2a0ccc73892e03b1d8876122a1e17971cfc4ea601c5abb2a209df1af04', 'tails': []}, '0xcf4fe0': {'file': 't219_live_equipment_cache_and_types.json', 'sha256': '8cd578504b3977db1a1bf767862350af38d546f2c1ce7203bc4b311f6772984f', 'tails': []}, '0xcf2e50': {'file': 't219_live_equipment_cache_and_types.json', 'sha256': 'a0c66091a5a50fff6652a96372de1cba53127bcfe66728a70b80b216be99d87a', 'tails': []}, '0x1409630': {'file': 't219_live_equipment_cache_and_types.json', 'sha256': 'e509fe659c825527e163129da7b5ed5e3d3020a12ea7f7de793a6b21bdb42a80', 'tails': []}}

def integer(x, lower, upper):
    if type(x) is not int or not lower <= x <= upper:
        raise ValueError("integer/range")
    return x

def normalize(v):
    integer(v, 0, (1 << 64)-1)
    if v & 0x80004003c1:
        if v & 0x40:
            v &= 0xfffffffffffffe7e
        elif v & 0x80:
            v &= 0xfffffffffffffefe
        elif v & 0x100:
            v &= 0xfffffffffffffffe
    return v

def capped(v):
    return min(MAXIMUM, max(-MAXIMUM, v))

def replay(documents):
    # Freeze actual native bytes. Calls are never executed by this replay.
    for address, rule in CONTRACT.items():
        document = documents[rule["file"]]
        flows = document.get("flows", document.get("leaf_flows", {}))
        f = flows[address]
        if f["unresolved_edges"] or f["external_tails"] != rule["tails"]:
            raise ValueError("unclosed flow")
        if hashlib.sha256(bytes.fromhex(f["raw_hex"])).hexdigest() != rule["sha256"]:
            raise ValueError("native bytes changed")
    live = documents["t219_live_equipment_cache_and_types.json"]
    guard = live["before"]
    if guard != live["after"] or guard["pid"] != 10288 or guard["base"] != "0x7ff758fc0000" or guard["country_index"] != 3:
        raise ValueError("fixture session changed")
    if any(guard["markers"].values()) or live["stable_dependency_count"] <= 0:
        raise ValueError("gate or unstable snapshot")
    for name in ("deployment", "occupation", "logistics", "operations", "countryresources"):
        if live["components"][name]["count"] != 0:
            raise ValueError("nonempty extra component out of proved scope")
    for rule in CONTRACT.values():
        doc = documents[rule["file"]]
        if doc["before"] != guard or doc["after"] != guard:
            raise ValueError("mixed-session evidence")
    types = live["types"]
    if len({t["name"] for t in types}) != len(types) or sorted(t["dense_index_598"] for t in types) != list(range(len(types))):
        raise ValueError("catalog bijection")
    byname = {t["name"]: t for t in types}
    caches = {c["logistics_slot_index"]: c for c in live["caches"]}
    for index in (15, 16):
        c = caches[index]
        if not len(types) == c["count"] == len(c["values_raw"]) or c["cap"] < c["count"]:
            raise ValueError("missing/partial dense cache; absent is not zero")
        for v in c["values_raw"]:
            integer(v, -(1 << 63), (1 << 63)-1)
    for req in live["requests"]:
        for part in ("need", "produced"):
            rows = req[part]
            if len({x["equipment_type"] for x in rows}) != len(rows):
                raise ValueError("duplicate request type")
            for row in rows:
                if row["equipment_type"] not in byname:
                    raise ValueError("unknown request type")
                integer(row["amount_raw"], 0, MAXIMUM)
    result = {}
    for name in SCOPE:
        t = byname[name]
        # Deliberately do not claim recursive/inherited or newly loaded types.
        if t["ptr"] != t["base_type_ptr"] or t["gate_5b5"] != 1:
            raise ValueError("archetype/assertion gate outside current proof")
        v = normalize(t["own_flags_5a0"] | t["extra_flags_5a8"])
        if not (v & 0x408000003c) or v & ((1 << 31) | 1) or t["special_44b"] != 0:
            raise ValueError("main/stock/special type gate")
        total = 0
        for req in live["requests"]:
            n = {x["equipment_type"]: x["amount_raw"] for x in req["need"]}.get(name, 0)
            p = {x["equipment_type"]: x["amount_raw"] for x in req["produced"]}.get(name, 0)
            total = capped(total+n)
            total = capped(total-p)
        if total < 0 or total % FIXED:
            raise ValueError("negative or fractional scoped demand")
        i = t["dense_index_598"]
        stored_stock = caches[15]["values_raw"][i]
        stored_balance = caches[16]["values_raw"][i]
        native_current = max(0, stored_stock)  # 1409630; NOT production stockpile parser output
        if native_current-total != stored_balance:
            raise ValueError("daily cache stale/mismatched; no current demand acceptance")
        result[name] = {"demanded": total//FIXED, "demand_raw": total,
                        "native_current_raw": native_current, "stored_balance_raw": stored_balance}
    return result
