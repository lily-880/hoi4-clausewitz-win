from pathlib import Path
import hashlib, json
inv = Path(r"D:\Michael Foo\钢四陆军总司令\态势信息读取能力清单.md")
raw = inv.read_bytes()
print("len", len(raw), "bom", raw[:3]==b"\xef\xbb\xbf", "crlf", b"\r\n" in raw, "lf_only", b"\n" in raw and b"\r\n" not in raw)
old = "| world.provinces.neighbors | 未验证 | 省份真实陆地邻接编号。 |"
new = "| world.provinces.neighbors | 已验证 | 当前己方师所在省份的陆地邻接编号，含渡河边，不含海与不可通行。 |"
# try both newline styles
text = raw.decode("utf-8-sig")
if old not in text:
    raise SystemExit("old line missing: "+repr([l for l in text.splitlines() if "neighbors" in l]))
if text.count(old) != 1:
    raise SystemExit("old line count %d" % text.count(old))
new_text = text.replace(old, new, 1)
# re-encode preserving BOM and newlines
nl = "\r\n" if raw.count(b"\r\n") else "\n"
# normalize to original newline
# If we decoded, splitlines lost endings. Rebuild from lines using original nl.
# Safer: replace in the exact encoded form.
if raw.startswith(b"\xef\xbb\xbf"):
    body = raw[3:]
    bom = b"\xef\xbb\xbf"
else:
    body = raw
    bom = b""
# detect encoding was utf-8
s = body.decode("utf-8")
if old not in s:
    raise SystemExit("old line missing in body")
s2 = s.replace(old, new, 1)
out = bom + s2.encode("utf-8")
# sanity: only this change
if raw.startswith(b"\xef\xbb\xbf"):
    assert out.startswith(b"\xef\xbb\xbf")
assert out != raw
# show diff size
print("old bytes", len(raw), "new bytes", len(out), "delta", len(out)-len(raw))
inv.write_bytes(out)
digest = hashlib.sha256(inv.read_bytes()).hexdigest()
print("SHA256", digest)
# recount
text2 = inv.read_text(encoding="utf-8-sig")
tables=0; fields=[]; verified=0
for l in text2.splitlines():
    if l.startswith("| 字段名 |"):
        tables += 1
        continue
    if l.startswith("| ---"):
        continue
    if l.startswith("| ") and l.count("|") >= 3:
        cols = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cols) >= 3 and cols[1] in ("已验证", "未验证"):
            fields.append(cols)
            if cols[1]=="已验证":
                verified += 1
print("tables", tables, "fields", len(fields), "verified", verified, "unverified", len(fields)-verified)
row=next(c for c in fields if c[0]=="world.provinces.neighbors")
print("neighbors row", row)
river=next(c for c in fields if c[0]=="world.provinces.has_river_crossing")
print("river row", river)
rec={"path": str(inv), "sha256": digest, "fields": len(fields), "tables": tables, "columns": 3, "verified": verified, "unverified": len(fields)-verified}
Path("research/t180_inventory_sha256.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("recorded")
