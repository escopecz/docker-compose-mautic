#!/usr/bin/env python3
"""Back up one stopped instance; test database restores in a disposable container."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
from render import inventory, MYSQL_IMAGE, ROOT


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def compose(*args):
    return ['docker', 'compose', '-f', str(ROOT/'compose.json'), '--profile', 'jobs', *args]


def backup(name, destination):
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    candidates = [name+'-'+role for role in ('web', 'cron', 'worker')]
    active = subprocess.check_output(compose('ps', '--status', 'running', '--services'), text=True).splitlines()
    active = [s for s in active if s in candidates]
    container = subprocess.check_output(compose('ps', '-a', '-q', name+'-web'), text=True).strip()
    if not container:
        raise RuntimeError('Start the web service before taking a backup')
    try:
        if active:
            run(compose('stop', '-t', '90', *active))
        with gzip.open(destination/'database.sql.gz', 'wb') as output:
            proc = subprocess.Popen(compose('exec', '-T', 'db', 'bash', '/opt/example/database-client.sh', 'dump', 'mautic_'+name), stdout=subprocess.PIPE)
            while chunk := proc.stdout.read(1024*1024):
                output.write(chunk)
            if proc.wait():
                raise RuntimeError('Database backup failed')
        with (destination/'application.tar.gz').open('wb') as output:
            image = subprocess.check_output(['docker','inspect','--format','{{.Image}}',container], text=True).strip()
            run(['docker','run','--rm','--network','none','--volumes-from',container+':ro',
                 '--entrypoint','tar',image,'-C','/var/www/html','-czf','-', 'config','docroot/media'], stdout=output)
        for filename in ('database.sql.gz', 'application.tar.gz'):
            with gzip.open(destination/filename, 'rb') as stream:
                while stream.read(1024*1024):
                    pass
        metadata = {'instance': name, 'image': image, 'sha256': {}}
        for filename in ('database.sql.gz', 'application.tar.gz'):
            with (destination/filename).open('rb') as stream:
                metadata['sha256'][filename] = hashlib.file_digest(stream, 'sha256').hexdigest()
        (destination/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    finally:
        if active:
            run(compose('start', *active))


def rehearse(name, directory):
    metadata = json.loads((directory/'manifest.json').read_text())
    if metadata['instance'] != name:
        raise ValueError('Backup belongs to a different instance')
    for filename in ('database.sql.gz', 'application.tar.gz'):
        with (directory/filename).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != metadata['sha256'][filename]:
                raise ValueError('Backup checksum mismatch')
    container = 'mautic-restore-'+uuid.uuid4().hex[:12]
    schema = 'mautic_'+name
    try:
        run(['docker','run','-d','--name',container,'--network','none',
             '-e','MYSQL_ROOT_PASSWORD_FILE=/run/secrets/mysql_root_password',
             '-v',str(ROOT/'secrets/mysql_root_password')+':/run/secrets/mysql_root_password:ro',
             '-v',str(ROOT/'secrets'/('db_'+schema))+':/run/secrets/db_'+schema+':ro',
             '-v',str(ROOT/'runtime')+':/opt/example:ro',
             '--tmpfs','/run/mysql-secrets:rw,noexec,nosuid,size=1m',
             '--entrypoint','bash',
             '--health-cmd','mysqladmin ping --silent','--health-interval','2s','--health-retries','90',
             MYSQL_IMAGE,'/opt/example/database-entrypoint.sh','mysqld','--event-scheduler=DISABLED','--local-infile=0'], stdout=subprocess.DEVNULL)
        import time
        for _ in range(120):
            status = subprocess.check_output(['docker','inspect','--format','{{.State.Health.Status}}',container], text=True).strip()
            if status == 'healthy':
                # TCP readiness excludes the entrypoint's temporary socket-only server.
                result = subprocess.run(['docker','exec',container,'bash','/opt/example/database-client.sh','query',schema], input='SELECT 1;',text=True,capture_output=True)
                if result.returncode == 0:
                    break
            time.sleep(2)
        else:
            raise RuntimeError('Disposable database did not become ready')
        query = ['docker','exec','-i',container,'bash','/opt/example/database-client.sh','query',schema]
        state = subprocess.check_output(query, input='SELECT @@event_scheduler;', text=True).strip()
        if state != 'DISABLED':
            raise RuntimeError('Event scheduler must be disabled before import')
        with gzip.open(directory/'database.sql.gz','rb') as source:
            proc = subprocess.Popen(['docker','exec','-i',container,'bash','/opt/example/database-client.sh','import',schema], stdin=subprocess.PIPE)
            try:
                while chunk := source.read(1024*1024):
                    proc.stdin.write(chunk)
            finally:
                proc.stdin.close()
            if proc.wait():
                raise RuntimeError('Restore failed; live database untouched')
        run(query, input='SELECT @@event_scheduler; SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();',text=True)
        print('Database restore passed; no application or jobs were started.')
    finally:
        # -v removes only this command's disposable anonymous database volume.
        subprocess.run(['docker','rm','-fv',container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == '__main__':
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['backup','rehearse'])
    parser.add_argument('instance')
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    if args.instance not in [i['name'] for i in inventory(ROOT/'instances.json')]:
        parser.error('Unknown instance')
    # Prevent simultaneous backup/rehearsal commands for the same instance.
    import fcntl
    lock = open(ROOT/('secrets/.backup-'+args.instance+'.lock'),'w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if args.action == 'backup':
        destination = args.directory or ROOT/'backups'/args.instance/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup(args.instance, destination)
        print('Private backup complete:', destination)
    elif args.directory:
        rehearse(args.instance, args.directory.resolve())
    else:
        parser.error('Rehearsal requires --directory')
