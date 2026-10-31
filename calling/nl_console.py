"""Natural language to Hearts of Iron IV 1.19 console commands.

The catalog is the game's own documentation
(documentation/console_commands_documentation.md), parsed into
calling/console_commands.json. This module turns a Chinese or English
request into the command line the console actually accepts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("console_commands.json")

# Longer names first so 意大利 is not eaten by a shorter token.
COUNTRIES = (
    ("埃塞俄比亚", "ETH"),
    ("捷克斯洛伐克", "CZE"),
    ("南斯拉夫", "YUG"),
    ("澳大利亚", "AST"),
    ("立陶宛", "LIT"),
    ("卢森堡", "LUX"),
    ("比利时", "BEL"),
    ("葡萄牙", "POR"),
    ("意大利", "ITA"),
    ("德意志", "GER"),
    ("西班牙", "SPR"),
    ("土耳其", "TUR"),
    ("罗马尼亚", "ROM"),
    ("匈牙利", "HUN"),
    ("保加利亚", "BUL"),
    ("加拿大", "CAN"),
    ("墨西哥", "MEX"),
    ("爱尔兰", "IRE"),
    ("阿富汗", "AFG"),
    ("不丹", "BHU"),
    ("海地", "HAI"),
    ("满洲", "MAN"),
    ("暹罗", "SIA"),
    ("苏联", "SOV"),
    ("美国", "USA"),
    ("英国", "ENG"),
    ("法国", "FRA"),
    ("德国", "GER"),
    ("日本", "JAP"),
    ("中国", "CHI"),
    ("波兰", "POL"),
    ("希腊", "GRE"),
    ("瑞典", "SWE"),
    ("挪威", "NOR"),
    ("芬兰", "FIN"),
    ("荷兰", "HOL"),
    ("丹麦", "DEN"),
    ("瑞士", "SWI"),
    ("奥地利", "AUS"),
    ("印度", "RAJ"),
    ("巴西", "BRA"),
    ("伊拉克", "IRQ"),
    ("伊朗", "PER"),
    ("沙特", "SAU"),
)

# (phrases, catalog name, token written to the console)
INTENTS = (
    (("瞬间建造", "即时建造", "一键建造", "无限建造"), "instantconstruction", "ic"),
    (("瞬间训练", "即时训练", "一键训练", "无限训练"), "instanttraining", "it"),
    (("省份提示", "调试提示", "省份调试", "提示调试"), "provtooltipdebug", "tdebug"),
    (("战争迷雾", "关掉迷雾", "关闭迷雾", "迷雾"), "fow", "fow"),
    (("显示省份", "省份编号", "省份id", "省份号"), "province_ids", "province_ids"),
    (("外交全接受", "外交全同意", "全部同意外交", "是先生"), "ai_accept", "yesman"),
    (("无视外交", "允许全部外交", "外交不限"), "allowdiplo", "allowdiplo"),
    (("自由国策", "任意国策"), "freefocuses", "ff"),
    (("国策不检查", "国策免检查"), "Focus.NoChecks", "Focus.NoChecks"),
    (("国策自动完成", "自动完成国策"), "Focus.AutoComplete", "Focus.AutoComplete"),
    (("忽略国策前置", "国策忽略前置"), "Focus.IgnorePrerequisites", "Focus.IgnorePrerequisites"),
    (("观察者", "观察模式", "旁观"), "observe", "observe"),
    (("瞬间造舰", "瞬间海军"), "instant_prepare", "instant_prepare"),
    (("瞬间改装", "舰船瞬间改装"), "instantshiprefit", "isr"),
    (("瞬间战争目标", "立刻战争目标", "瞬间造战争目标"), "instant_wargoal", "instant_wargoal"),
    (("点图标就研究", "点一下就研究", "点击研究"), "research_on_icon_click", "research_on_icon_click"),
    (("研究全部", "全部研究", "研究所有"), "research", "research"),
    (("研究变快", "研究只要1点"), "research_fast", "research_fast"),
    (("政治点", "政治点数", "政治力量"), "pp", "pp"),
    (("指挥点", "指挥力"), "cp", "cp"),
    (("人力",), "manpower", "manpower"),
    (("三军经验", "陆海空经验", "陆军经验", "海军经验", "空军经验"), "xp", "xp"),
    (("稳定度", "稳定"), "add_stability", "st"),
    (("战争支持度", "战争支持"), "add_war_support", "ws"),
    (("燃料", "燃油"), "fuel", "fuel"),
    (("核弹", "原子弹"), "nukes", "nuke"),
    (("吞并",), "annex", "annex"),
    (("傀儡", "附庸"), "puppet", "puppet"),
    (("白和", "白和平", "停战"), "whitepeace", "wp"),
    (("扮演", "切换到", "切到", "换成"), "tag", "tag"),
    (("传送到", "传送", "瞬移"), "teleport", "tp"),
    (("地区给", "州给", "归属给", "把州"), "setowner", "setowner"),
    (("控制省份", "省份控制", "控制权给"), "setcontroller", "setcontroller"),
    (("加核心", "添加核心"), "add_core", "add_core"),
    (("去掉核心", "移除核心"), "remove_core", "remove_core"),
    (("触发事件", "执行事件"), "event", "event"),
    (("开关ai", "切换ai", "关闭ai", "打开ai"), "ai", "ai"),
    (("开关天气", "天气模拟"), "weather", "weather"),
    (("最新装备",), "add_latest_equipment", "ale"),
    (("给装备", "装备"), "add_equipment", "ae"),
    (("fa",), "fa", "fa"),
)

AMOUNT_COMMANDS = {
    "pp", "cp", "manpower", "xp", "add_stability", "add_war_support",
    "fuel", "fuel_gain", "nukes", "add_cic_bank", "compliance",
    "add_latest_equipment",
}
TAG_COMMANDS = {"tag", "annex", "puppet", "whitepeace", "add_opinion"}
_NOT_TAGS = {
    "all", "tag", "pp", "the", "and", "for", "ic", "it", "ae", "ale", "st", "ws",
    "xp", "cp", "wp", "tp", "ff", "op", "ai", "fa", "pid",
}


def load_catalog() -> list[dict]:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return data["commands"]


def _numbers(text: str) -> list[int]:
    found = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*([万亿])?", text):
        value = float(match.group(1))
        unit = match.group(2)
        if unit == "万":
            value *= 10000
        elif unit == "亿":
            value *= 100000000
        found.append(int(value) if value == int(value) else value)
    return found


def _countries(text: str) -> list[str]:
    hits = []
    occupied = [False] * len(text)
    for name, tag in COUNTRIES:
        start = 0
        while True:
            at = text.find(name, start)
            if at < 0:
                break
            if not any(occupied[at:at + len(name)]):
                for i in range(at, at + len(name)):
                    occupied[i] = True
                hits.append((at, tag))
            start = at + len(name)
    for match in re.finditer(r"\b([A-Za-z]{3})\b", text):
        token = match.group(1).lower()
        if token in _NOT_TAGS:
            continue
        hits.append((match.start(), token.upper()))
    hits.sort()
    tags = []
    for _, tag in hits:
        if tag not in tags:
            tags.append(tag)
    return tags


def _by_name(catalog: list[dict]) -> dict[str, dict]:
    return {row["name"]: row for row in catalog}


def _contains(text: str, phrase: str) -> bool:
    if phrase.isascii() and len(phrase) <= 4:
        return re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(phrase)}(?![A-Za-z0-9_])",
            text,
            re.I,
        ) is not None
    return phrase.lower() in text.lower()


def _match_intent(text: str) -> tuple[str, str, str] | None:
    best = None
    best_len = 0
    for phrases, name, token in INTENTS:
        for phrase in phrases:
            if _contains(text, phrase) and len(phrase) > best_len:
                best = (phrase, name, token)
                best_len = len(phrase)
    return best


def _match_catalog_token(text: str, catalog: list[dict]) -> dict | None:
    lowered = text.lower()
    tokens = set(re.findall(r"[a-z][a-z0-9_.]*", lowered))
    for row in catalog:
        names = [row["name"].lower(), *[a.lower() for a in row["aliases"]]]
        if any(name in tokens or name in lowered for name in names if len(name) >= 2):
            # Prefer a real word hit over a short alias buried in another word.
            if any(name in tokens for name in names):
                return row
    return None


def _render(name: str, token: str, text: str, row: dict) -> tuple[str, str]:
    nums = _numbers(text)
    tags = _countries(text)
    note = ""
    if name == "research" and ("全部" in text or re.search(r"\ball\b", text, re.I)):
        return "research all", note
    if name == "event":
        ident = re.search(r"[A-Za-z][\w.]*\.[\w.]+", text)
        if ident:
            extra = f" {tags[0]}" if tags else ""
            return f"event {ident.group(0)}{extra}", note
        return "event <事件id>", "还缺事件 id，例如 event news.1"
    if name in AMOUNT_COMMANDS:
        if not nums:
            return token, f"还缺数量，例如 {token} 500"
        return f"{token} {nums[0]}", note
    if name in TAG_COMMANDS:
        if not tags:
            return token, f"还缺国家，例如 {token} GER"
        return f"{token} {tags[0]}", note
    if name == "setowner":
        if not tags or not nums:
            return "setowner <TAG> <state id>", "还缺国家和地区号，例如 setowner POL 10"
        return f"setowner {tags[0]} {nums[0]}", note
    if name == "setcontroller":
        if not tags or not nums:
            return "setcontroller <TAG> <province id>", "还缺国家和省份号，例如 setcontroller GER 100"
        return f"setcontroller {tags[0]} {nums[0]}", note
    if name == "teleport":
        if not nums:
            return "tp <province id>", "还缺省份号，例如 tp 758"
        return f"tp {nums[0]}", note
    if name == "add_core" or name == "remove_core":
        if not nums:
            return f"{token} <province id>", "还缺省份号"
        return f"{token} {nums[0]}", note
    if name == "add_equipment":
        if not nums:
            return "ae <数量> <装备id>", "还缺数量和装备 id，例如 ae 1000 infantry_equipment"
        skip = {token.lower(), name.lower(), *[a.lower() for a in row.get("aliases", [])]}
        words = re.findall(r"[A-Za-z][\w.]*", text)
        equip = next((word for word in words if word.lower() not in skip), None)
        if not equip:
            return f"ae {nums[0]} <装备id>", "还缺装备 id，例如 infantry_equipment"
        return f"ae {nums[0]} {equip}", note
    if name == "fow" and nums:
        return f"fow {nums[0]}", note
    return token, note


def translate(text: str, catalog: list[dict] | None = None) -> dict:
    text = (text or "").strip()
    catalog = catalog if catalog is not None else load_catalog()
    index = _by_name(catalog)
    if not text:
        return {"ok": False, "line": "", "detail": "说一句想做的事，例如：瞬间建造，或者给自己 500 政治点"}
    intent = _match_intent(text)
    row = None
    token = None
    if intent:
        _, name, token = intent
        row = index.get(name)
    if row is None:
        row = _match_catalog_token(text, catalog)
        if row:
            token = row["aliases"][0] if row["aliases"] and len(row["aliases"][0]) <= 6 else row["name"]
            name = row["name"]
    if row is None:
        return {
            "ok": False,
            "line": "",
            "detail": "官方命令表里没有对上这句话。可以说得更具体，例如：吞并波兰、加 500 政治点、战争迷雾。",
        }
    if token is None:
        token = row["name"]
        name = row["name"]
    line, missing = _render(name, token, text, row)
    detail = row["description"] or row["name"]
    if row["arguments"]:
        detail = f"{detail} 参数：{row['arguments']}"
    if not row["in_release"]:
        detail = f"{detail}（正式版里没有这条）"
    if missing:
        detail = f"{missing}。{detail}"
    return {
        "ok": not missing,
        "line": line,
        "name": row["name"],
        "detail": detail,
        "in_release": row["in_release"],
    }
