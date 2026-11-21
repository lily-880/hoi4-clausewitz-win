from pathlib import Path

def show(path, n=12000):
    p = Path(path)
    t = p.read_text(encoding="utf-8", errors="ignore")
    print("=" * 80)
    print(path, "LEN", len(t))
    print(t[:n])
    print()

# t191 first
show("research/t191_checkpoint.md")
