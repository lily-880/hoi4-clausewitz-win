# also offsets.py CA_PATH comment; input_loaded_fields end for where to add reader
from pathlib import Path
# how many tests currently
import subprocess
print("looking at CA_PATH and capture order notes")
t = Path("calling/offsets.py").read_text(encoding="utf-8")
for i,l in enumerate(t.splitlines(),1):
    if "CA_PATH" in l or "0x200" in l and "PATH" in l:
        print(f"{i}|{l}")
