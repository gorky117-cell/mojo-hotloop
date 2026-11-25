"""Check local links in changed docs; remote accessibility is separate."""
from pathlib import Path
import re
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
names=subprocess.check_output(["git","-C",str(root),"diff","--name-only","HEAD"]).decode().splitlines()
names+=subprocess.check_output(["git","-C",str(root),"ls-files","--others","--exclude-standard"]).decode().splitlines()
errors=[];count=0
for name in sorted(set(names)):
    p=root/name
    if p.suffix!=".md" or not p.is_file():continue
    for label,target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)",p.read_text()):
        if target.startswith(("http:","https:","mailto:","#")):continue
        target=target.split("#",1)[0]
        if not target:continue
        count+=1
        if not (p.parent/target).resolve().exists():errors.append(name+" -> "+target)
if errors:
    print("\n".join(errors));sys.exit(1)
print("Checked",count,"local documentation links; remote URLs not certified by this check.")
