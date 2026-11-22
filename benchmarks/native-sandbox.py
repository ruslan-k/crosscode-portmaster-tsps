from pathlib import Path
import hashlib
import json
import os
import shutil

p = Path('/mnt/SDCARD/Roms/PORTS/crosscode-qx')
d = p / 'perf-next-20261122'
d.mkdir(exist_ok=True)
backup = d / 'baseline'
backup.mkdir(exist_ok=True)
assets = p / 'gamedata/assets'
files = [p / 'quixjs.aarch64', p / 'port.toml', p / 'ccx-boot.js', p.parent / 'CrossCode.sh', assets / 'ccx-boot.js'] + sorted(assets.glob('cc.save*'))
manifest = {}
for src in files:
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    manifest[str(src)] = digest
    if src.name != 'quixjs.aarch64':
        dest = backup / ('effective-boot.js' if src == assets / 'ccx-boot.js' else src.name)
        if dest.exists():
            assert hashlib.sha256(dest.read_bytes()).hexdigest() == digest, str(src)
        else:
            shutil.copy2(src, dest)
(backup / 'manifest.json').write_text(json.dumps(manifest, indent=2))
# Only immutable asset directories are linked. NW.js resolves this directory,
# not the production directory, so all save writes stay in the sandbox.
sandbox = Path('/tmp/cc-perf-next/assets')
sandbox.mkdir(parents=True, exist_ok=True)
for src in assets.iterdir():
    dest = sandbox / src.name
    if src.name.startswith('cc.save'):
        if dest.is_symlink():
            dest.unlink()
        shutil.copy2(src, dest)
    elif not dest.exists():
        dest.symlink_to(src)
boot = sandbox / 'ccx-boot.js'
if boot.is_symlink():
    boot.unlink()
shutil.copy2(assets / 'ccx-boot.js', boot)
config = (p / 'port.toml').read_text().replace('game_dir  = "gamedata/assets"', 'game_dir  = "/tmp/cc-perf-next/assets"').replace('cache_dir = "cache/gamedata"', 'cache_dir = "/mnt/SDCARD/Roms/PORTS/crosscode-qx/perf-next-20261122/cache"')
assert '/tmp/cc-perf-next/assets' in config
(d / 'port.toml').write_text(config)
print(json.dumps({'sandbox': str(sandbox), 'production_sha256': manifest}, indent=2))
