# DeskBridge launch copy

Ready-to-copy posts for the maintainer. These are drafts, not evidence that
anything has been posted to X. Links point to the public project.

## Main X post

My RTX 5090 + local Qwen + custom AI harness helped build DeskBridge: open-source keyboard, mouse & clipboard sharing for Windows + Fedora, powered by Deskflow. Moving between my PCs feels so smooth. Prerelease out now:
https://github.com/jamesarslan/deskbridge-public
#OpenSource #LocalAI

## Follow-up thread

1. Two computers, one keyboard and mouse. Move left from my Windows screen onto Fedora, keep typing, then move back. Each PC runs its own apps. DeskBridge makes setup and daily Start/Stop easier around Deskflow's input-sharing engine.

2. The build setup: Qwen 27B running on my RTX 5090, connected to development tools through my custom OMP harness. Local model generation, real tool use, and an existing open-source engine made a practical project possible.

3. Honest credits: Deskflow provides input sharing. The development preset also used OpenRouter Jev for decisions, and Codex handled a separate review and fixes. This was a mixed-model workflow, with local Qwen doing generation. No AI or GPU is needed to run the app.

4. The reviewed prerelease includes guided setup, Start/Stop launchers, saved TLS pairing, configuration preservation and reconnect handling. Local tests and real TLS checks passed. CI is blocked by an account billing lock; the test matrix records the limits.

5. Try the Windows + Fedora prerelease, report bugs, or contribute. It's free and community-maintained. Current scope is desktop input sharing; remote video and headless access aren't supported product claims.
https://github.com/jamesarslan/deskbridge-public/releases/tag/v0.2.0-rc2

## Demo caption

One keyboard. One mouse. Windows on the right, Fedora on the left.
DeskBridge + Deskflow make both computers feel like one desk.
Built with help from local Qwen on my RTX 5090 and a custom AI harness.

## Suggested demo

Record a short clip showing both monitors: move the Windows pointer left
onto Fedora, type into a blank editor, copy harmless sample text back to
Windows, then return right. Show the actual experience. Close private apps
and notifications before recording. A clip of the real desk is stronger
evidence than an invented benchmark or latency claim.

## Positioning

- Project: DeskBridge — open-source keyboard and mouse sharing for Windows and Linux.
- Short description: Free software KVM setup for a Windows + Fedora desk, powered by Deskflow.
- Discoverability terms: keyboard sharing, mouse sharing, software KVM, Windows Linux, Fedora, GNOME Wayland, clipboard sharing, Deskflow, local AI, Qwen, RTX 5090.
- Credit the existing engine and distinguish development AI from runtime requirements.
- Describe the project as free and community-maintained; MIT permits commercial reuse and no incorporated nonprofit status is claimed.
- Keep prerelease status visible. Do not claim fully local development, REA use, remote video, headless support, zero latency or universal OS/layout coverage.
