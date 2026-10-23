#!/usr/bin/env python3
"""Validate inventory and render candidate Compose files. Never deploy or read secrets."""
import argparse
import copy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def inventory(root=ROOT):
    result = {}
    unique = {key: set() for key in ('domain', 'port', 'database')}
    required = {'id', 'domain', 'host', 'port', 'database', 'source_version',
                'target_version', 'image', 'plugins_to_validate', 'migration_path', 'status'}
    for path in sorted((root / 'instances').glob('*.json')):
        item = json.loads(path.read_text())
        if set(item) != required:
            raise ValueError(f'{path.name}: unexpected or missing fields')
        slug = item['id']
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', slug) or path.stem != slug:
            raise ValueError('Invalid instance identity')
        if not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*', item['domain']):
            raise ValueError('Invalid domain')
        if item['host'] != '165.232.83.73':
            raise ValueError('Host is not in the reviewed destination allowlist')
        if type(item['port']) is not int or not 8001 <= item['port'] <= 8090:
            raise ValueError('Invalid backend port')
        if not re.fullmatch(r'mautic_[a-z][a-z0-9_]{0,24}', item['database']):
            raise ValueError('Invalid database name')
        if not re.fullmatch(r'mautic/mautic@sha256:[a-f0-9]{64}', item['image']):
            raise ValueError('Application image must use a reviewed immutable digest')
        for key in ('source_version', 'target_version'):
            if not re.fullmatch(r'\d+\.\d+\.\d+', item[key]):
                raise ValueError('Invalid version')
        route = item['migration_path']
        if not isinstance(route, list) or not route or route[0] != item['source_version'] or route[-1] != item['target_version']:
            raise ValueError('Migration path must match source and target')
        if not all(isinstance(v, str) and re.fullmatch(r'\d+\.\d+(?:\.\d+)?', v) for v in route):
            raise ValueError('Invalid migration checkpoint')
        majors = [int(v.split('.')[0]) for v in route]
        if any(b - a not in (0, 1) for a, b in zip(majors, majors[1:])):
            raise ValueError('Do not skip major-version checkpoints')
        if item['status'] != 'preparation-only':
            raise ValueError('Production activation has not been implemented or reviewed')
        if not isinstance(item['plugins_to_validate'], list) or not all(
                isinstance(p, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9]*Bundle', p)
                for p in item['plugins_to_validate']):
            raise ValueError('Invalid plugin inventory')
        for key, seen in unique.items():
            if item[key] in seen:
                raise ValueError(f'Duplicate {key}')
            seen.add(item[key])
        result[slug] = item
    if not result:
        raise ValueError('Empty instance inventory')
    return result


def app_compose(item):
    slug = item['id']
    base = {
        'image': item['image'], 'restart': 'unless-stopped',
        'env_file': [f'/etc/mautic/{slug}.env'],
        'environment': {
            'MAUTIC_DB_HOST': 'mysql', 'MAUTIC_DB_PORT': '3306',
            'MAUTIC_DB_DATABASE': item['database'], 'MAUTIC_DB_USER': item['database'],
            'DOCKER_MAUTIC_RUN_MIGRATIONS': 'false',
        },
        'volumes': ['app:/var/www/html', 'config:/var/www/html/config',
                    'media:/var/www/html/docroot/media', 'logs:/var/www/html/var/logs'],
        'networks': ['database', 'outbound'],
        'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}},
    }
    services = {}
    for name, role in [('web', 'mautic_web'), ('cron', 'mautic_cron'), ('worker', 'mautic_worker')]:
        service = copy.deepcopy(base)
        service['environment']['DOCKER_MAUTIC_ROLE'] = role
        if name == 'web':
            service['ports'] = [f"127.0.0.1:{item['port']}:80"]
        else:
            service['profiles'] = ['jobs']
        services[name] = service
    return {
        'name': f'mautic-{slug}', 'services': services,
        'networks': {
            'database': {'external': True, 'name': f'mautic-db-{slug}'},
            'outbound': {},
        },
        # External volumes must be explicitly populated and verified before start.
        'volumes': {part: {'external': True, 'name': f'mautic_{slug}_{part}'}
                    for part in ('app', 'config', 'media', 'logs')},
    }


def database_compose(items, root=ROOT):
    cfg = json.loads((root / 'infrastructure/mysql.json').read_text())
    if not re.fullmatch(r'mysql@sha256:[a-f0-9]{64}', cfg['image']):
        raise ValueError('MySQL must be pinned by digest')
    if cfg['volume'] != 'mautic_shared_mysql84' or cfg['secret_file'] != '/etc/mautic/mysql-root-password':
        raise ValueError('Unreviewed database volume or secret path')
    networks = {slug: {'external': True, 'name': f'mautic-db-{slug}'} for slug in items}
    return {
        'name': 'mautic-database',
        'services': {'mysql': {
            'image': cfg['image'], 'restart': 'unless-stopped',
            'environment': {'MYSQL_ROOT_PASSWORD_FILE': '/run/secrets/mysql_root_password'},
            'secrets': ['mysql_root_password'], 'volumes': ['data:/var/lib/mysql'],
            'networks': {slug: {'aliases': ['mysql']} for slug in items},
            'healthcheck': {'test': ['CMD-SHELL', 'mysqladmin ping --silent'],
                            'interval': '10s', 'timeout': '5s', 'retries': 12},
            'logging': {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}},
        }},
        'networks': networks,
        'volumes': {'data': {'external': True, 'name': cfg['volume']}},
        'secrets': {'mysql_root_password': {'file': cfg['secret_file']}},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate', 'plan', 'render-app', 'render-database'])
    parser.add_argument('--instance')
    args = parser.parse_args()
    items = inventory()
    database = database_compose(items)
    if args.action == 'validate':
        print(f'Validated {len(items)} instances; preparation only, no deployment actions.')
    elif args.action == 'render-database':
        print(json.dumps(database, indent=2))
    else:
        if args.instance not in items:
            parser.error('--instance must name an instance in the inventory')
        item = items[args.instance]
        if args.action == 'render-app':
            print(json.dumps(app_compose(item), indent=2))
        else:
            print(json.dumps({'instance': item, 'deployment_enabled': False,
                              'required_gates': ['inventory custom plugins/themes', 'isolated local restore',
                                                'upgrade each major checkpoint', 'verify application and record counts',
                                                'repeat on final frozen source backup', 'per-site maintenance and rollback rehearsal']}, indent=2))


if __name__ == '__main__':
    main()
