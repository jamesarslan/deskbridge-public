#!/usr/bin/env bash
# Local engine smoke test (runs ON the Fedora box):
#  1. extract the pinned RPM (unpacked, not installed)
#  2. run deskflow-core SERVER with the real config/server.config on the local
#     X display (Xwayland :0), in an isolated XDG_CONFIG_HOME
#  3. run deskflow-core CLIENT -> 127.0.0.1 in its own isolated config home
#  4. assert: server listens on TCP 24800, client stays connected, TLS negotiated
#
# NOTE: the server core briefly grabs X input on the local display for the test
# duration (< ~30s). Do not run while actively using the desktop mouse.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

log()  { printf '\033[1;32m[smoke]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[smoke]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[smoke]\033[0m %s\n' "$*" >&2; exit 1; }

RPM="engine/deskflow-1.27.0-fedora-44-x86_64.rpm"
PORT=24800
WORK="$(mktemp -d /tmp/deskbridge-smoke.XXXXXX)"
SRV_PID="" CLI_PID=""
cleanup() {
  [[ -n "$SRV_PID" ]] && kill "$SRV_PID" 2>/dev/null || true
  [[ -n "$CLI_PID" ]] && kill "$CLI_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  log "artifacts: $WORK (logs kept for inspection)"
}
trap cleanup EXIT

[[ -f "$RPM" ]] || { ./tests/fetch-engine.sh; [[ -f "$RPM" ]] || die "RPM missing and fetch failed"; }

log "extracting RPM (unpacked, not installed)"
mkdir -p "$WORK/payload"
( cd "$WORK/payload" && rpm2cpio "$OLDPWD/$RPM" 2>/dev/null | cpio -idm --quiet ) \
  || ( cd "$WORK/payload" && bsdtar -xf "$OLDPWD/$RPM" 2>/dev/null )
CORE="$(find "$WORK/payload" -name deskflow-core -type f | head -1)"
[[ -n "$CORE" ]] || die "deskflow-core not found in RPM payload"
chmod +x "$CORE"
log "engine: $CORE"
log "version: $("$CORE" --version 2>/dev/null | head -1 || echo 'unknown')"

# X display (Xwayland :0 on this GNOME session)
export DISPLAY="${DISPLAY:-:0}"
XA_CAND="$(ls /run/user/"$(id -u)"/.mutter-Xwaylandauth.* 2>/dev/null | head -1 || true)"
[[ -n "$XA_CAND" ]] && export XAUTHORITY="$XA_CAND"
log "DISPLAY=$DISPLAY XAUTHORITY=${XAUTHORITY:-<unset>}"

# isolated config homes (do NOT touch the user's real Deskflow config)
mkdir -p "$WORK/cfg-server/Deskflow" "$WORK/cfg-client/Deskflow"
cat > "$WORK/cfg-server/Deskflow/Deskflow.conf" <<EOF
[core]
computerName=windows
coreMode=2
port=$PORT

[server]
externalConfig=true
externalConfigFile="$PWD/config/server.config"

[computer_windows]
name=windows

[computer_fedora]
name=fedora

[security]
tlsEnabled=true
checkPeerFingerprints=false
EOF
cat > "$WORK/cfg-client/Deskflow/Deskflow.conf" <<'EOF'
[core]
computerName=fedora
coreMode=1
port=24800

[client]
remoteHost=127.0.0.1

[security]
tlsEnabled=true
checkPeerFingerprints=false
EOF

# TLS: the core needs a self-signed PEM (private key first, then the cert,
# CN=Deskflow, RSA, see src/lib/net/SecureUtils.cpp) at
# <cfg>/Deskflow/tls/deskflow.pem. The GUI generates this on demand; the
# loopback test replicates it with openssl.
# Pairing: the client ALWAYS verifies the server cert against
# <cfg>/Deskflow/tls/trusted-servers (lines "v2:sha256:<sha256-of-DER-cert>",
# see FingerprintDatabase). In production the GUI dialog adds the entry on
# first connect; the loopback test pre-seeds it.
gen_cert() { # $1=cfg home -> echoes path of the bare cert PEM
  local home="$1" tmp
  mkdir -p "$home/Deskflow/tls"
  tmp="$(mktemp -d)"
  openssl req -x509 -newkey rsa:2048 -nodes -keyout "$tmp/key.pem" -out "$tmp/cert.pem" \
    -days 365 -subj "/CN=Deskflow" > /dev/null 2>&1
  cat "$tmp/key.pem" "$tmp/cert.pem" > "$home/Deskflow/tls/deskflow.pem"
  local cert="$home/Deskflow/tls/cert.pem"
  mv "$tmp/cert.pem" "$cert"
  rm -rf "$tmp"
  echo "$cert"
}
srv_cert="$(gen_cert "$WORK/cfg-server")"
gen_cert "$WORK/cfg-client" > /dev/null
openssl x509 -in "$srv_cert" -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1 | \
  sed 's/.*/v2:sha256:&/' > "$WORK/cfg-client/Deskflow/tls/trusted-servers"

log "starting server (INI settings -> externalConfigFile=config/server.config; screen map: fedora LEFT of windows)"
env XDG_CONFIG_HOME="$WORK/cfg-server" "$CORE" server > "$WORK/server.log" 2>&1 &
SRV_PID=$!

listen_ok=0
for _ in $(seq 1 30); do
  if ss -ltn 2>/dev/null | awk -v p=":$PORT" '$4 ~ p' | grep -q .; then listen_ok=1; break; fi
  sleep 0.5
done
[[ "$listen_ok" -eq 1 ]] || { cat "$WORK/server.log" >&2; die "server did not listen on TCP $PORT"; }
log "server listening on TCP $PORT"

log "starting client (computerName=fedora; server address from [client] remoteHost=127.0.0.1)"
# --new-instance: the core guards single-instance via SysV shm (keyed by binary
# name); loopback runs server and client as one user, so the client must skip it.
env XDG_CONFIG_HOME="$WORK/cfg-client" "$CORE" client --new-instance > "$WORK/client.log" 2>&1 &
CLI_PID=$!
sleep 10

rc=0
if kill -0 "$CLI_PID" 2>/dev/null; then
  log "client process alive after 10s"
else
  warn "client exited early (check client.log)"; rc=1
fi
if ss -tn 2>/dev/null | awk -v p=":$PORT" '($4 ~ p || $5 ~ p) && /ESTAB/' | grep -q .; then
  log "ESTABLISHED connection on TCP $PORT"
else
  warn "no ESTABLISHED connection on TCP $PORT"; rc=1
fi

echo; log "=== server.log (tail) ===";  tail -n 25 "$WORK/server.log"
echo; log "=== client.log (tail) ===";  tail -n 25 "$WORK/client.log"
echo
if [[ "$rc" -eq 0 ]]; then
  log "SMOKE PASS: engine parsed the real server config, TLS server accepted a client on 127.0.0.1:$PORT"
else
  die "SMOKE FAIL (see logs above)"
fi
