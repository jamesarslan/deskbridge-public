# NOTICE

DeskBridge is a thin setup layer (installers, helpers, configs, docs) around the
unmodified **Deskflow** engine.

## Bundled upstream components (unmodified)

- **Deskflow v1.27.0** — https://github.com/deskflow/deskflow (release tag `v1.27.0`)
  - `engine/deskflow-1.27.0-win-x64.msi` (Windows x64 installer)
  - `engine/deskflow-1.27.0-fedora-44-x86_64.rpm` (Fedora 44 x86_64)
  - License: GPL-2.0-only, with component licenses in `licenses/` of the upstream repo
    (GPL-2.0-only, LGPL-2.1-only, MIT, OpenSSL exception). See
    https://github.com/deskflow/deskflow/blob/master/COPYING and its `LICENSES/` directory.
  - Engine files are downloaded by the build (CI) from the pinned upstream release
    URLs and verified against `ci/manifest.json` (sha256 + size). They are never
    modified by this project.

## This project's own files

Everything else in this repository (tools/, config/, ci/, tests/, docs/,
workflows, README, STATUS) is MIT-licensed, see `LICENSE`.
