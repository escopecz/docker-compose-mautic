"""Keep local plugins/themes without replacing updated Composer-managed bundles."""
import json
import pathlib
import shutil
import sys
old, new = map(pathlib.Path, sys.argv[1:])
packages = json.loads((old / 'vendor/composer/installed.json').read_text())
packages = packages.get('packages', packages) if isinstance(packages, dict) else packages
managed = {pathlib.Path(p['install-path']).name for p in packages if p.get('type') in ('mautic-plugin', 'mautic-theme')}
for category in ('plugins', 'themes'):
    for source in (old / 'docroot' / category).iterdir():
        if source.is_dir() and source.name not in managed:
            target = new / 'docroot' / category / source.name
            shutil.copytree(source, target, dirs_exist_ok=True)
            print(f'Preserved custom {category}: {source.name}')
