"""Hash publishable repository artifacts; never include local profiler captures."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
excluded={'.git','build','__pycache__','scratch','counter-captures'}
files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
       for p in root.rglob('*') if p.is_file() and not excluded.intersection(p.relative_to(root).parts)
       and p.name!='sha256.json'}
(root/'common/sha256.json').write_text(json.dumps(files,indent=2))
print(f'Hashed {len(files)} publishable files; local captures excluded.')
