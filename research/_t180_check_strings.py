from pathlib import Path
# verify asserted instruction strings exist
checks = {
 "research/_t180_clip_NeighborAdjs_size_0xe90560.txt": [
  "mov rax, qword ptr [rdi + 0x70]",
  "mov edx, dword ptr [r12 + rax + 8]",
  "add r12, 0x30",
  "cmp eax, dword ptr [rdi + 0x7c]",
 ],
 "research/_t180_clip_0x14a6540.txt": [
  "lea r10, [rax + rax*2]",
  "add r10, r10",
  "mov byte ptr [rax + r10*8 + 0x10], r8b",
 ],
 "research/_t180_clip_0xab3660.txt": [
  "xor r12b, r12b",
  "sete r12b",
  "add r12b, r12b",
  "mov r12b, 3",
  "mov r12b, 1",
  "mov r12b, 4",
  "movzx r8d, r12b",
  "call 0x14a6540",
 ],
}
for fn, needles in checks.items():
    t=Path(fn).read_text(encoding="utf-8")
    for n in needles:
        print(("OK " if n in t else "MISS"), fn.split("_t180_")[-1], repr(n))
# syntax check patched files
import py_compile
for f in ["calling/input_loaded_fields.py","calling/input_capture_live.py","research/test_t180_input_neighbors.py"]:
    py_compile.compile(f, doraise=True)
    print("compiled", f)
