#!/usr/bin/env python3
"""Render a private Compose configuration from a reviewed instance inventory."""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import secrets

MYSQL_IMAGE = 'mysql@sha256:76f0358884cb92d9a086d24e5671c38048d3fef40f2588703d73eb55392d6b69'
APP_IMAGE = 'mautic-example:7.2.1'
ROOT = Path(__file__).resolve().parents[1]


def inventory(path):
    data = json.loads(Path(path).read_text())
    if set(data) != {'instances'} or not data['instances']:
        raise ValueError('Expected a nonempty instances list')
    seen = {key: set() for key in ('name', 'domain', 'port')}
    for item in data['instances']:
        if set(item) != {'name', 'domain', 'port', 'trusted_proxies'}:
            raise ValueError('Unexpected instance fields')
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,23}', item['name']):
            raise ValueError('Invalid instance name')
        if not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*', item['domain']):
            raise ValueError('Invalid domain')
        if type(item['port']) is not int or not 1024 <= item['port'] <= 65535:
            raise ValueError('Invalid loopback port')
        if not isinstance(item['trusted_proxies'], list):
            raise ValueError('Expected explicit proxy addresses')
        for proxy in item['trusted_proxies']:
            ipaddress.ip_address(proxy)  # No REMOTE_ADDR or trust-all networks.
        for key in seen:
            if item[key] in seen[key]:
                raise ValueError('Duplicate '+key)
            seen[key].add(item[key])
    return data['instances']


def render(items):
    result = {'services': {}, 'volumes': {'database': {}}, 'networks': {},
              'secrets': {'mysql_root_password': {'file': './secrets/mysql_root_password'}}}
    db = {'image': MYSQL_IMAGE, 'restart': 'unless-stopped',
          'environment': {'MYSQL_ROOT_PASSWORD_FILE': '/run/secrets/mysql_root_password'},
          'entrypoint': ['bash', '/opt/example/database-entrypoint.sh'],
          'command': ['mysqld', '--event-scheduler=DISABLED', '--local-infile=0'],
          'tmpfs': ['/run/mysql-secrets:rw,noexec,nosuid,size=1m'],
          'secrets': ['mysql_root_password'], 'networks': {},
          'volumes': ['database:/var/lib/mysql', './runtime:/opt/example:ro'],
          'healthcheck': {'test': ['CMD', 'mysqladmin', 'ping', '--silent'], 'interval': '5s', 'timeout': '5s', 'retries': 30}}
    result['services']['db'] = db
    for item in items:
        name = item['name']; schema = 'mautic_'+name; net = 'db_'+name
        secret = 'db_'+schema
        result['secrets'][secret] = {'file': './secrets/'+secret}
        db['secrets'].append(secret)
        db['networks'][net] = {'aliases': ['mysql']}
        result['networks'][net] = {'internal': True}
        result['networks']['outbound_'+name] = {}
        volumes = []
        for part, target in [('config','config'), ('files','docroot/media/files'), ('images','docroot/media/images'), ('logs','var/logs')]:
            volume = name+'_'+part
            result['volumes'][volume] = {}
            volumes.append(volume+':/var/www/html/'+target)
        for role in ('web','cron','worker'):
            service = {'image': APP_IMAGE, 'platform': 'linux/amd64',
                       'restart': 'unless-stopped', 'depends_on': {'db': {'condition': 'service_healthy'}},
                       'environment': {'DOCKER_MAUTIC_ROLE': 'mautic_'+role, 'MAUTIC_DB_DATABASE': schema,
                                       'MAUTIC_DOMAIN': item['domain'], 'TRUSTED_PROXIES': json.dumps(item['trusted_proxies']),
                                       'APP_ENV': 'prod', 'APP_DEBUG': '0',
                                       'DOCKER_MAUTIC_WORKERS_CONSUME_EMAIL': '1',
                                       'DOCKER_MAUTIC_WORKERS_CONSUME_HIT': '1',
                                       'DOCKER_MAUTIC_WORKERS_CONSUME_FAILED': '0'},
                       'secrets': [{'source': secret, 'target': 'database_password'}],
                       'networks': [net, 'outbound_'+name], 'volumes': volumes,
                       'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}}}
            if role == 'web':
                service['build'] = {'context': '.', 'dockerfile': 'Dockerfile'}
                service['ports'] = [f"127.0.0.1:{item['port']}:80"]
            else:
                service['profiles'] = ['jobs']
            result['services'][name+'-'+role] = service
    return result


def initialize(items, directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    for name in ['mysql_root_password']+['db_mautic_'+i['name'] for i in items]:
        path = directory/name
        if not path.exists():
            # Exclusive creation; never rotate a running database's credentials.
            with path.open('x') as stream:
                path.chmod(0o600)
                stream.write(secrets.token_hex(24)+'\n')
        if not re.fullmatch(r'[a-f0-9]{48}\n?', path.read_text()):
            raise ValueError('Invalid secret file: '+name)
        path.chmod(0o600)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(ROOT/'instances.json'))
    parser.add_argument('--init-secrets', action='store_true')
    args = parser.parse_args()
    items = inventory(args.config)
    if args.init_secrets:
        initialize(items, ROOT/'secrets')
    (ROOT/'compose.json').write_text(json.dumps(render(items), indent=2)+'\n')
    print('Rendered compose.json; no containers started.')
