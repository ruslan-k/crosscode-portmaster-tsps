#!/usr/bin/env python3
"""One isolated CrossCode scene; real per-frame CSV is emitted by the test runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

P = Path('/mnt/SDCARD/Roms/PORTS/crosscode-qx')
D = P / 'perf-next-20261122'
sys.path.insert(0, str(P))
# Upstream console.py is installed beside port.toml on the device.
from console import Console  # pyright: ignore[reportMissingImports]

parser = argparse.ArgumentParser()
parser.add_argument('label')
parser.add_argument('--binary', default=str(D / 'quix-diag'))
parser.add_argument('--backend', default='dummy', choices=('dummy', 'sdl'))
parser.add_argument('--map', default='arid.forest-1')
parser.add_argument('--marker', default='')
parser.add_argument('--position', help='Explicit map position x,y,level for a stationary benchmark')
parser.add_argument('--verify', action='store_true')
parser.add_argument('--exercise', action='store_true')
parser.add_argument('--seconds', type=int, default=60)
parser.add_argument('--warmup', type=int, default=30)
args = parser.parse_args()
assert args.label.replace('-', '').replace('_', '').isalnum()
out = D / 'runs' / args.label
out.mkdir(parents=True, exist_ok=False)
if args.backend == 'sdl':
    for proc in Path('/proc').iterdir():
        if proc.name.isdigit():
            try:
                cmd = (proc / 'cmdline').read_bytes()
            except OSError:
                continue
            assert b'mainui.py' not in cmd or b'-msgDisplayRealtimePort' in cmd, 'MainUI still owns DRM'
for save in (D / 'baseline').glob('cc.save*'):
    shutil.copy2(save, Path('/tmp/cc-perf-next/assets') / save.name)
sock = '/tmp/cc-next.sock'
if os.path.exists(sock):
    raise RuntimeError('stale or active test socket; inspect before retry')
env = dict(os.environ)
env.update(QUIXJS_FONT=str(P / 'fonts/DejaVuSans-Bold.ttf'),
           LD_LIBRARY_PATH=str(P / 'libs.aarch64') + ':' + env.get('LD_LIBRARY_PATH', ''),
           QUIX_FAST_OPAQUE_BLIT='1', CC_PERF_CSV=str(out / 'frames.csv'),
           SDL_AUDIODRIVER='alsa', AUDIODEV='plughw:0,0',
           SDL_GAMECONTROLLER_IGNORE_DEVICES='0x045e/0x028e')
if args.verify:
    env['CC_VERIFY_BLEND'] = '/tmp/cc-verify-' + args.label
    assert not Path(env['CC_VERIFY_BLEND']).exists()
state_expr = '''JSON.stringify({map:ig.game.mapName,teleporting:ig.game.teleporting.active,player:ig.game.playerEntity&&ig.game.playerEntity.coll.pos,camera:ig.game.screen,hp:ig.game.playerEntity&&ig.game.playerEntity.params&&ig.game.playerEntity.params.currentHp,input:ig.input.actions,pad:navigator.getGamepads()[0]&&{axes:navigator.getGamepads()[0].axes,buttons:navigator.getGamepads()[0].buttons.map(function(b){return b.value;})},gameDelegate:ig.system.delegate===ig.game,loading:sc.model.isLoading(),scale:ig.system.scale,width:ig.system.width,height:ig.system.height,contextWidth:ig.system.contextWidth,contextHeight:ig.system.contextHeight,canvas:[ig.system.canvas.width,ig.system.canvas.height],options:sc.options&&sc.options.values})'''
meta = {'completed': False, 'args': vars(args), 'binary_sha256': hashlib.sha256(Path(args.binary).read_bytes()).hexdigest(), 'env': {k:v for k,v in env.items() if k.startswith(('QUIX_', 'CC_PERF'))}}
def census():
    result = {}
    for key, path in [('cpu_khz','/sys/devices/system/cpu/cpu4/cpufreq/scaling_cur_freq'), ('governor','/sys/devices/system/cpu/cpu4/cpufreq/scaling_governor'), ('meminfo','/proc/meminfo'), ('vmstat','/proc/vmstat')]:
        try: result[key] = Path(path).read_text()
        except OSError: pass
    result['thermal'] = {str(x):x.read_text() for x in Path('/sys/class/thermal').glob('thermal_zone*/temp')}
    return result
with (out / 'runtime.log').open('w') as log:
    cmd = [args.binary, '-b', args.backend, '--debug=' + sock, '--fps', '-c', str(D / 'port.toml')]
    if args.backend == 'sdl': cmd.append('--fullscreen')
    proc = subprocess.Popen(cmd, cwd=str(P), env=env, stdout=log, stderr=subprocess.STDOUT)
    meta['pid'] = proc.pid
    try:
        deadline = time.monotonic() + 90
        console = None
        while time.monotonic() < deadline:
            if proc.poll() is not None: raise RuntimeError('runtime exited: ' + str(proc.returncode))
            try:
                console = Console(sock)
                console.sock.settimeout(20)
                ok, result = console.command('eval !!(typeof sc !== "undefined" && sc.savePreset && typeof ig !== "undefined" && ig.game && ig.game.loadStart)')
                if ok and result == ['true']: break
                console.sock.close()
                console = None
            except OSError:
                pass
            time.sleep(1)
        assert console is not None, 'game initialization timed out'
        def command(s):
            ok, lines = console.command(s)
            assert ok, (s, lines)
            return '\n'.join(lines)
        command('eval sc.savePreset.load(5); "loaded"')
        time.sleep(14)
        command('press Enter'); time.sleep(3)
        command('press Enter'); time.sleep(8)
        if args.map != 'bergen-trail.path-8':
            position = 'new ig.TeleportPosition(' + json.dumps(args.marker) + ')' if args.marker else 'null'
            if args.position:
                x, y, level = [int(v) for v in args.position.split(',')]
                position = '(function(){var p=new ig.TeleportPosition();p.setFromData(null,{x:%d,y:%d,z:0},{x:0,y:1},%d,0,{x:16,y:16});return p;})()' % (x, y, level)
            command('eval ig.game.teleport(' + json.dumps(args.map) + ',' + position + '); "teleport-called"')
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            state = json.loads(command('eval ' + state_expr))
            if state['map'] == args.map and not state['teleporting'] and state['gameDelegate'] and not state['loading']: break
            time.sleep(1)
        else: raise RuntimeError('map load timed out')
        time.sleep(args.warmup)
        meta['state_start'] = json.loads(command('eval ' + state_expr))
        assert meta['state_start']['canvas'] == [568, 320], meta['state_start']
        assert meta['state_start']['map'] == args.map and meta['state_start']['gameDelegate'] and not meta['state_start']['loading'], meta['state_start']
        assert meta['state_start'].get('pad') is None, 'controller-ignore hint did not take effect'
        command('shot ' + str(out / 'canvas-start.png'))
        if args.backend == 'sdl':
            subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(out / 'kms-start.png')],check=True,stdout=log,stderr=log)
        meta['census_start'] = census()
        if args.verify:
            Path(env['CC_VERIFY_BLEND']).touch(exist_ok=False)
        meta['window_start_ms'] = time.monotonic() * 1000
        meta['state_samples'] = []
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            time.sleep(min(5, max(0, deadline - time.monotonic())))
            current = json.loads(command('eval ' + state_expr))
            meta['state_samples'].append({'mono_ms':time.monotonic()*1000, 'state':current})
            assert current['map'] == args.map and current['gameDelegate'] and not current['loading'], current
            if not args.exercise:
                assert current['player'] == meta['state_start']['player'], 'player moved; scene is not stationary'
        meta['window_end_ms'] = time.monotonic() * 1000
        meta['census_end'] = census()
        meta['runtime_memory'] = Path('/proc/%d/status' % proc.pid).read_text()
        meta['state_end'] = json.loads(command('eval ' + state_expr))
        assert meta['state_end']['map'] == args.map
        command('shot ' + str(out / 'canvas-end.png'))
        if args.backend == 'sdl':
            subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(out / 'kms-end.png')],check=True,stdout=log,stderr=log)
        if args.exercise:
            before = json.loads(command('eval ' + state_expr))
            command('down KeyD'); time.sleep(.6); command('up KeyD'); time.sleep(.7)
            after = json.loads(command('eval ' + state_expr))
            assert after['map'] == before['map'] and after['player']['x'] > before['player']['x'] + 5, (before['player'], after['player'])
            meta['movement_check'] = {'before':before['player'], 'after':after['player']}
            command('shot ' + str(out / 'canvas-movement.png'))
            if args.backend == 'sdl':
                subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(out / 'kms-movement.png')],check=True,stdout=log,stderr=log)
        try: command('quit')
        except ConnectionError: pass
        proc.wait(timeout=15)
        assert proc.returncode == 0, proc.returncode
        meta['completed'] = True
    finally:
        if proc.poll() is None:
            # Popen holds the exact child; never kill by process name.
            proc.terminate()
            try: proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(timeout=8)
        meta['exit_code'] = proc.returncode
        (out / 'metadata.json').write_text(json.dumps(meta, indent=2))
        if os.path.exists(sock): os.unlink(sock)
        if args.verify and Path(env['CC_VERIFY_BLEND']).exists():
            Path(env['CC_VERIFY_BLEND']).unlink()
print(json.dumps({'label':args.label,'exit':proc.returncode,'state':meta.get('state_start'),'out':str(out)},indent=2))
