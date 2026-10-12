#!/usr/bin/env python3
"""Real engine/systemd/TLS lifecycle test on a separate virtual X11 desktop.

Requires Fedora's installed Deskflow >=1.27, Xvfb and a user systemd manager.
Never uses the real desktop or production profile. This is NOT a Wayland test.
"""
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader('integration_app', str(ROOT/'src/deskbridge'))
spec = importlib.util.spec_from_loader(loader.name, loader)
db = importlib.util.module_from_spec(spec);loader.exec_module(db)
for binary in ('Xvfb', 'deskflow-core', 'systemctl', 'openssl', 'ss'):
    if not shutil.which(binary):
        sys.exit(f'Missing integration prerequisite: {binary}')
tag = 'review-' + uuid.uuid4().hex[:10]
server, client = db.Paths(tag+'-server'), db.Paths(tag+'-client')
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0));port = sock.getsockname()[1]
display = next(i for i in range(90, 200) if not pathlib.Path(f'/tmp/.X11-unix/X{i}').exists())
xvfb = subprocess.Popen(['Xvfb', f':{display}', '-screen', '0', '1280x720x24', '-ac', '-nolisten', 'tcp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
dropins = []
def wait(predicate, message, seconds=20):
    end = time.monotonic()+seconds
    while time.monotonic()<end:
        if predicate(): return
        time.sleep(.25)
    raise AssertionError(message)
def cli(paths, *args, ok=True):
    result = subprocess.run([sys.executable, str(ROOT/'src/deskbridge'), '--profile', paths.profile, '--json', *args], capture_output=True, text=True, timeout=30)
    if ok and result.returncode:
        raise AssertionError(f'{args[0]} failed: {result.stderr} {result.stdout}')
    return json.loads(result.stdout) if result.stdout.strip() else {}
def established():
    result = subprocess.run(['ss','-Htn','state','established'], capture_output=True, text=True)
    return any(f':{port}' in line for line in result.stdout.splitlines())
try:
    wait(lambda: pathlib.Path(f'/tmp/.X11-unix/X{display}').exists(), 'Xvfb did not start')
    for paths, role, name in ((server,'server','host'), (client,'client','guest')):
        state = dict(db.default_state(paths.profile), role=role, name=name, peer='127.0.0.1', port=port, engine='core', wizard_done=True,
                     map={'host': {'left':'guest'}, 'guest': {'right':'host'}} if role=='server' else {})
        db.save_state(paths,state);db.write_engine_conf(paths,state)
        paths.engine_conf.write_text(paths.engine_conf.read_text().replace('level = Info', 'level = Debug'))
        if role=='server': db.write_server_map(paths,state)
        assert not db.ensure_cert(paths).get('error')
        dropin = db.unit_file(paths).with_name(paths.unit+'.service.d')
        dropin.mkdir(parents=True);dropins.append(dropin)
        (dropin/'virtual-display.conf').write_text(f'[Service]\nEnvironment=DISPLAY=:{display}\nEnvironment=QT_QPA_PLATFORM=xcb\nUnsetEnvironment=WAYLAND_DISPLAY XDG_SESSION_TYPE\n')
    db.trust_add(server, db.cert_fingerprint(client));db.trust_add(client, db.cert_fingerprint(server))
    before = {str(p):p.read_bytes() for p in (client.cert,client.trust_db,server.cert,server.trust_db)}
    cli(server,'start');cli(client,'start')
    wait(established, 'Pinned TLS loopback connection not established')
    wait(lambda: client.log_file.exists() and 'connected to server' in client.log_file.read_text().lower(), 'Deskflow protocol connection absent')
    assert not db.validate_conf(server,db.load_state(server))
    assert not db.validate_conf(client,db.load_state(client))
    # Idempotent starts retain the same supervised process.
    pid = db.unit_main_pid(client);cli(client,'start');assert db.unit_main_pid(client)==pid
    cli(client,'autostart','on');assert db.autostart_enabled(client)
    cli(client,'autostart','off');assert not db.autostart_enabled(client)
    # Real supervisor recovery and client reconnect after a server crash.
    old_pid = db.unit_main_pid(server);os.kill(old_pid,signal.SIGKILL)
    wait(lambda: db.unit_main_pid(server) not in (None,old_pid), 'Server supervisor did not restart', 25)
    wait(established,'Client did not reconnect',25)
    cli(client,'restart');wait(established,'Client restart did not reconnect')
    cli(client,'stop');cli(client,'stop');cli(server,'stop')
    for name, data in before.items(): assert pathlib.Path(name).read_bytes()==data, 'TLS identity/trust changed'
    # Upgrade/setup is done only while stopped and preserves permission values.
    text = client.engine_conf.read_text()
    import configparser,io
    cp=configparser.ConfigParser(interpolation=None);cp.optionxform=str;cp.read_string(text)
    cp['client']['xdpRestoreToken']='synthetic-preservation-test'
    cp['gui']['ignoreMissingKeyboardLayouts']='true'
    buffer=io.StringIO();cp.write(buffer);client.engine_conf.write_text(buffer.getvalue())
    cli(client,'setup','--yes','--autostart','off')
    flat=db.read_engine_conf(client)
    assert flat['client.xdpRestoreToken']=='synthetic-preservation-test'
    assert flat['gui.ignoreMissingKeyboardLayouts']=='true'
    assert not db.autostart_enabled(client)
    cli(client,'repair')
    for name, data in before.items(): assert pathlib.Path(name).read_bytes()==data
    for paths in (client,server):
        cli(paths,'uninstall');cli(paths,'uninstall')
        assert paths.cert.exists() and paths.trust_db.exists(), 'Uninstall removed pairing'
        assert not db.unit_file(paths).exists()
    print('PASS: actual Deskflow on Xvfb; generated server/client settings; pinned TLS; repeated start/stop/restart; crash recovery/reconnect; opt-in autostart; upgrade/repair preservation; repeat uninstall.')
    print('Scope: isolated X11 loopback, not physical input or GNOME Wayland permission testing.')
except Exception:
    for paths in (server,client):
        print(paths.profile, 'recent test log:', db.log_tail(paths, 15), file=sys.stderr)
    raise
finally:
    for paths in (client,server):
        db.stop_engine(paths)
        if db.unit_file(paths).exists():
            subprocess.run(['systemctl','--user','disable',paths.unit],capture_output=True)
            db.unit_file(paths).unlink()
        for dropin in dropins:
            if dropin.exists() and dropin.name.startswith(tag): shutil.rmtree(dropin)
        if paths.app_home.is_relative_to(pathlib.Path.home()/'.config/DeskBridge') and paths.profile.startswith(tag):
            shutil.rmtree(paths.app_home,ignore_errors=True)
        if paths.log_file.exists(): paths.log_file.unlink()
    subprocess.run(['systemctl','--user','daemon-reload'],capture_output=True)
    xvfb.terminate();xvfb.wait(timeout=10)
