from pathlib import Path
import hashlib
p=Path('research/t205_checkpoint.md');s=p.read_text(encoding='utf8');b=Path('research/t205_block2.md').read_text(encoding='utf8');assert '## Block2'not in s;p.write_text(s+b,encoding='utf8');print(hashlib.sha256(p.read_bytes()).hexdigest())
