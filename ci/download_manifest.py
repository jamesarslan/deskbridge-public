#!/usr/bin/env python3
"""Download pinned Deskflow engine artifacts (ci/manifest.json) into a stage dir.

Verifies sha256 and size for every artifact. Exits nonzero on any mismatch.

Usage: python3 ci/download_manifest.py [stage_dir]   (default: stage)
Layout: <stage>/win/engine/<msi>, <stage>/fedora44/engine/<rpm>
"""
import hashlib
import json
import pathlib
import sys
import urllib.request

DESTS = {
    "windows": ("win", "engine"),
    "fedora44": ("fedora44", "engine"),
}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    stage = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else root / "stage"
    manifest = json.loads((root / "ci" / "manifest.json").read_text())

    for key, art in manifest["artifacts"].items():
        dest = stage.joinpath(*DESTS[key]) / art["file"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            existing = sha256_file(dest)
            if existing == art["sha256"] and dest.stat().st_size == art["size"]:
                print(f"cached ok: {dest} sha256={existing}")
                continue
            print(f"cache mismatch for {dest}, re-downloading", file=sys.stderr)
            dest.unlink()
        print(f"downloading {art['url']}")
        with urllib.request.urlopen(art["url"], timeout=900) as r:
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        got = sha256_file(dest)
        if got != art["sha256"]:
            sys.exit(f"SHA256 mismatch for {art['file']}: got {got}, want {art['sha256']}")
        size = dest.stat().st_size
        if size != art["size"]:
            sys.exit(f"size mismatch for {art['file']}: got {size}, want {art['size']}")
        print(f"verified: {dest} sha256={got} size={size}")


if __name__ == "__main__":
    main()
