#!/usr/bin/env python3
"""Private, schema-scoped Cronfig backups; no shared-server exports or public logs."""
import datetime,fcntl,gzip,hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
lock=open('/run/lock/mautic-cronfig-backup.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
root=Path('/opt/mautic/cronfig');base=Path('/root/mautic-cronfig-backups');base.mkdir(mode=0o700,exist_ok=True)
if not (root/'activated.json').exists():raise SystemExit('Instance is not active')
timestamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');dest=base/timestamp;dest.mkdir(mode=0o700)
pw=Path('/etc/mautic/cronfig-database-password').read_text().strip()
with gzip.open(dest/'database.sql.gz','wb') as out,open(dest/'dump.log','wb') as err:
    proc=subprocess.Popen(['docker','exec','-e','MYSQL_PWD='+pw,'mautic_db','mysqldump','--no-defaults','-h127.0.0.1','-umautic_cronfig','--single-transaction','--routines','--triggers','--no-tablespaces','--set-gtid-purged=OFF','--hex-blob','mautic_cronfig'],stdout=subprocess.PIPE,stderr=err)
    shutil.copyfileobj(proc.stdout,out)
    if proc.wait():raise RuntimeError('Private backup dump failed')
with tarfile.open(dest/'application.tar.gz','w:gz') as archive:
    for name in ['config','media','plugins','themes','runtime','compose.live.json','release','activated.json']:
        archive.add(root/name,arcname=name)
    archive.add('/etc/nginx/sites-available/m.cronfig.io',arcname='nginx.conf')
lines=[]
for name in ['database.sql.gz','application.tar.gz']:
    f=dest/name
    with gzip.open(f,'rb') as stream:
        while stream.read(1024*1024):pass
    with f.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    lines.append(digest+'  '+name);f.chmod(0o600)
(dest/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
(dest/'complete').touch()
complete=sorted(p for p in base.iterdir() if p.is_dir() and len(p.name)==16 and (p/'complete').exists())
for old in complete[:-3]:shutil.rmtree(old)
print('Cronfig private database/files backup verified.')
