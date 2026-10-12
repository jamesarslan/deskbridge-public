#!/usr/bin/env bash
# Download the pinned engine artifacts (ci/manifest.json) flat into engine/ and
# verify sha256 + size. (CI uses ci/download_manifest.py with its stage layout.)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 - <<'EOF'
import hashlib, json, pathlib, urllib.request

m = json.load(open('ci/manifest.json'))
out_dir = pathlib.Path('engine')
out_dir.mkdir(exist_ok=True)
for art in m['artifacts'].values():
    out = out_dir / art['file']
    if out.exists():
        h = hashlib.sha256(out.read_bytes()).hexdigest()
        if h == art['sha256'] and out.stat().st_size == art['size']:
            print(f"cached ok: {out}")
            continue
        out.unlink()
    print(f"downloading {art['url']}")
    with urllib.request.urlopen(art['url'], timeout=900) as r, open(out, 'wb') as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    assert h == art['sha256'], f"sha256 mismatch: {h}"
    assert out.stat().st_size == art['size'], "size mismatch"
    print(f"verified: {out} sha256={h}")
EOF
