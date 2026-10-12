#!/usr/bin/env python3
"""Assemble DeskBridge bundles (win64 + fedora44) from repo + stage artifacts.

Reads ci/manifest.json (pinned engine digests) and VERSION. Produces, in
<stage>/release/:
  deskbridge-win64-<ver>.zip
  deskbridge-fedora44-<ver>.zip
  SHA256SUMS      (zip hashes + inner engine hashes)
  RELEASE.md      (release notes: versions, digests, source ref)

Usage: python3 ci/package_bundles.py [stage_dir]   (default: stage)
Env:   GITHUB_REF (source tag), optional.
"""
import hashlib
import json
import os
import pathlib
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUNDLE_FILES = [
    "README.md",
    "NOTICE.md",
    "LICENSE",
    "VERSION",
    "licenses/GPL-2.0-only.txt",
    "config/server.conf",
    "config/server.config",
    "config/client.conf",
    "src/deskbridge",
    "tools/DeskBridge.ps1",
    "ARCHITECTURE.md",
    "docs/TESTING.md",
    "docs/SETUP-WINDOWS.md",
    "docs/SETUP-FEDORA.md",
    "docs/WAYLAND.md",
]

# download_manifest.py writes windows under stage/win; zips use the doc names
STAGE_DIRS = {"windows": "win", "fedora44": "fedora44"}
ZIP_NAMES = {"windows": "win64", "fedora44": "fedora44"}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_zip(name: str, stage: pathlib.Path, bundle: pathlib.Path, root_name: str) -> pathlib.Path:
    out = stage / "release" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    # Fixed entry timestamps: byte-reproducible bundles (content mtimes vary
    # per build, e.g. SHA256SUMS.engine); file mode bits are preserved.
    ts = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(bundle.rglob("*")):
            if not p.is_file():
                continue
            arcname = (pathlib.Path(root_name) / p.relative_to(bundle)).as_posix()
            zi = zipfile.ZipInfo(arcname, date_time=ts)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (p.stat().st_mode & 0xFFFF) << 16
            z.writestr(zi, p.read_bytes())
    return out


def main() -> None:
    stage = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "stage"
    manifest = json.loads((ROOT / "ci" / "manifest.json").read_text())
    version = json.loads((ROOT / "VERSION").read_text())["version"]
    src_ref = os.environ.get("GITHUB_REF", "local")

    bundles = {}
    for key, art in manifest["artifacts"].items():
        engine = stage / STAGE_DIRS[key] / "engine" / art["file"]
        if not engine.exists():
            sys.exit(f"missing stage artifact: {engine} (run ci/download_manifest.py first)")
        got = sha256_file(engine)
        if got != art["sha256"]:
            sys.exit(f"stage artifact {engine} does not match manifest sha256")
        bundle = stage / "bundle" / key
        if bundle.exists():
            shutil.rmtree(bundle)
        (bundle / "engine").mkdir(parents=True)
        shutil.copy2(engine, bundle / "engine" / art["file"])
        for rel in BUNDLE_FILES:
            src = ROOT / rel
            if not src.exists():
                sys.exit(f"missing repo file for bundle: {rel}")
            dst = bundle / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            if rel == "src/deskbridge":
                dst.chmod(0o755)
        # per-bundle checksums of the engine
        (bundle / "SHA256SUMS.engine").write_text(f"{art['sha256']}  engine/{art['file']}\n")
        bundles[key] = (bundle, art)

    release = stage / "release"
    release.mkdir(parents=True, exist_ok=True)
    sums = []
    notes = [
        f"# DeskBridge v{version}",
        "",
        "Deskflow v%s KVM bridge: Windows server (keyboard/mouse) -> Fedora client." % manifest["version"],
        "Fedora monitor is LEFT of Windows. TLS on by default; first-run fingerprint pairing.",
        "",
        "Source ref: %s" % src_ref,
        "",
        "## Bundles",
        "",
    ]
    for key, (bundle, art) in bundles.items():
        name = f"deskbridge-{ZIP_NAMES[key]}-{version}.zip"
        out = build_zip(name, stage, bundle, f"deskbridge-{ZIP_NAMES[key]}-{version}")
        # Validate the actual ZIP rather than only the staging directory.
        with zipfile.ZipFile(out) as archive:
            entries = set(archive.namelist())
            required = [*BUNDLE_FILES, f"engine/{art['file']}", "SHA256SUMS.engine"]
            for rel in required:
                if f"deskbridge-{ZIP_NAMES[key]}-{version}/{rel}" not in entries:
                    sys.exit(f"incomplete bundle {out}: missing {rel}")
        h = sha256_file(out)
        sums.append(f"{h}  {name}")
        notes += [
            f"- **{name}** — {key} bundle (engine: `{art['file']}`)",
            f"  - engine sha256 `{art['sha256']}` (verified against upstream release v{manifest['version']})",
            f"  - bundle sha256 `{h}`",
        ]
    notes += [
        "",
        "## Install",
        "",
        "- Windows server PC: unzip, right-click PowerShell -> Run as administrator -> `cd` to folder -> `\\tools\\DeskBridge.ps1 install` -> `\\tools\\DeskBridge.ps1 start` (see docs/SETUP-WINDOWS.md).",
        "- Fedora client: unzip, `sudo dnf install -y engine/*.rpm`, `src/deskbridge setup --yes --role client --peer <windows-ip> --name <name>` -> `src/deskbridge start` (see docs/SETUP-FEDORA.md).",
        "- First connection: confirm the TLS fingerprint dialog on both sides (compare with `src/deskbridge fingerprint` / `\\tools\\DeskBridge.ps1 fingerprint`); on Fedora approve the GNOME input-permission prompt once.",
        "",
        "## Known limitations (v%s)" % version,
        "",
        "- Single-operator desk setup only (one server, one client).",
        "- Windows side not machine-verified at build time (manual steps; engine is the unmodified upstream MSI).",
        "- Wayland client path verified against official docs + installed dependency versions, not a live second machine.",
        "- Cosmetic (upstream): on a Wayland server the cursor may not hide at the screen edge (compositor limitation).",
    ]
    (release / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    (release / "RELEASE.md").write_text("\n".join(notes) + "\n")
    for s in sums:
        print(s)


if __name__ == "__main__":
    main()
