"""Provision and remove only this workflow run's disposable rehearsal droplet."""
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

name = f"mautic-veetr-v2-test-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
base = 'https://api.digitalocean.com/v2/'

def api(path, method='GET', data=None):
    request = urllib.request.Request(base + path, method=method,
        headers={'Authorization': 'Bearer ' + os.environ['DIGITALOCEAN_TOKEN'], 'Content-Type': 'application/json'},
        data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response) if response.status != 204 else None

def export(key, value):
    with open(os.environ['GITHUB_ENV'], 'a') as stream:
        stream.write(f'{key}={value}\n')

if sys.argv[1] == 'create':
    root = Path(os.environ['RUNNER_TEMP'])
    cloud = {
        'ssh_authorized_keys': [(root / 'deploy.pub').read_text().strip(), (root / 'transfer.pub').read_text().strip()],
        'ssh_keys': {'ed25519_private': (root / 'test-host').read_text(), 'ed25519_public': (root / 'test-host.pub').read_text().strip()},
        'package_update': True,
        'packages': ['docker.io', 'docker-compose-v2'],
        'runcmd': [['systemctl', 'enable', '--now', 'docker'], ['touch', '/root/rehearsal-ready']],
    }
    droplet = api('droplets', 'POST', {'name': name, 'region': 'ams3', 'size': 's-2vcpu-4gb',
        'image': 'ubuntu-24-04-x64', 'backups': False, 'monitoring': False,
        'tags': ['mautic-upgrade-rehearsal'], 'user_data': '#cloud-config\n' + json.dumps(cloud)})['droplet']
    export('TEST_DROPLET_ID', droplet['id'])
    for _ in range(90):
        droplet = api(f"droplets/{droplet['id']}")['droplet']
        addresses = [n['ip_address'] for n in droplet['networks']['v4'] if n['type'] == 'public']
        if droplet['status'] == 'active' and addresses:
            export('TEST_HOST', addresses[0])
            print('Disposable test droplet is active.')
            break
        time.sleep(5)
    else:
        raise RuntimeError('Test droplet did not become ready')
else:
    # Exact name is scoped to this workflow run, including partial creation failures.
    droplets = api('droplets?name=' + name)['droplets']
    for droplet in droplets:
        if droplet['name'] != name or 'mautic-upgrade-rehearsal' not in droplet['tags']:
            raise RuntimeError('Refusing cleanup of a nonmatching droplet')
        api(f"droplets/{droplet['id']}", 'DELETE')
    for _ in range(30):
        if not api('droplets?name=' + name)['droplets']:
            break
        time.sleep(2)
    else:
        raise RuntimeError('Test droplet deletion was not confirmed')
    print('Disposable test droplet deleted; no snapshots or backups were created.')
