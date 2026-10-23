#!/usr/bin/env python3
"""Scoped Cronfig deployment. Run through the manual workflow; diagnostics stay private."""
import argparse,fcntl,hashlib,json,os,re,shutil,socket,subprocess,time
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['stage','activate','verify','maintenance','renew-certificate'])
p.add_argument('release');a=p.parse_args()
if not re.fullmatch(r'[a-z0-9-]{1,40}',a.release):raise SystemExit('Invalid release')
if socket.gethostname()!='mautic-veetr-v2' or os.geteuid()!=0:raise SystemExit('Wrong server or user')
lock=open('/run/lock/mautic-cronfig-deploy.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
root=Path('/opt/mautic/cronfig');payload=Path('/root/cronfig-payload-'+a.release)
repo=Path(__file__).resolve().parents[1];container='mautic-cronfig-web';schema='mautic_cronfig'

def run(args,**kw):
    return subprocess.run(args,check=True,**kw)
def capture(args):return subprocess.check_output(args,text=True).strip()
def mysql(sql,root_user=False):
    if root_user:
        env=json.loads(capture(['docker','inspect','mautic_db']))[0]['Config']['Env']
        pw=next(x.split('=',1)[1] for x in env if x.startswith('MYSQL_ROOT_PASSWORD='));user='root'
    else:pw=(payload/'database-password').read_text().strip();user=schema
    return subprocess.check_output(['docker','exec','-i','-e','MYSQL_PWD='+pw,'mautic_db','mysql','--no-defaults','-h127.0.0.1','-u'+user,'-N',*([] if root_user else [schema])],input=sql,text=True).strip()
def compose(live):
    dest=root/('compose.live.json' if live else 'compose.staged.json')
    dest.write_text(capture(['python3',str(repo/'scripts/cronfig-compose.py'),'--root',str(root),*(['--live'] if live else [])])+'\n')
    return ['docker','compose','-f',str(dest)]
def nginx(live):
    cert='/etc/nginx/ssl/cronfig-migration'
    if Path('/etc/letsencrypt/live/m.cronfig.io/fullchain.pem').exists():cert='/etc/letsencrypt/live/m.cronfig.io'
    location='proxy_pass http://127.0.0.1:8002; proxy_set_header Host $host; proxy_set_header X-Forwarded-Proto https; proxy_set_header X-Forwarded-For $remote_addr; proxy_set_header X-Real-IP $remote_addr; proxy_read_timeout 120s;' if live else 'add_header Retry-After 300 always; return 503;'
    shutil.copyfile(root/'runtime/nginx-logging.conf','/etc/nginx/conf.d/cronfig-logging.conf')
    text=f'''server {{ listen 80; server_name m.cronfig.io; location ^~ /.well-known/acme-challenge/ {{ root /var/www/letsencrypt; }} location / {{ return 301 https://$host$request_uri; }} }}
server {{ listen 443 ssl; server_name m.cronfig.io; access_log /var/log/nginx/cronfig-access.log cronfig_without_query; ssl_certificate {cert}/fullchain.pem; ssl_certificate_key {cert}/privkey.pem; include /etc/letsencrypt/options-ssl-nginx.conf; ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; client_max_body_size 25m; location / {{ {location} }} }}
'''
    site=Path('/etc/nginx/sites-available/m.cronfig.io');previous=site.read_bytes() if site.exists() else None
    site.write_text(text)
    enabled=Path('/etc/nginx/sites-enabled/m.cronfig.io')
    if not enabled.exists():enabled.symlink_to(site)
    try:run(['nginx','-t']);run(['systemctl','reload','nginx'])
    except Exception:
        if previous is not None:site.write_bytes(previous)
        else:enabled.unlink(missing_ok=True);site.unlink(missing_ok=True)
        raise

def healthy():
    def http(path):
        return capture(['docker','exec',container,'curl','-sS','--max-time','30','-H','Host: m.cronfig.io','-H','X-Forwarded-Proto: https','-o','/tmp/cronfig-health.html','-w','%{http_code}','http://127.0.0.1'+path])
    for _ in range(36):
        try:
            if http('/s/login')=='200':break
        except subprocess.CalledProcessError:pass
        time.sleep(5)
    else:raise RuntimeError('Cronfig login did not return HTTP 200')
    for path in ['/form/generate.js?id=1','/form/generate.js?id=9']:
        if http(path)!='200':raise RuntimeError('Cronfig form did not return HTTP 200')
    version=capture(['docker','exec','-w','/var/www/html',container,'php','bin/console','--version'])
    if not version.startswith('Mautic 7.2.1'):raise RuntimeError('Unexpected application version')
    run(['curl','-fsS','--max-time','30','-o','/dev/null','https://m.veetr.com/s/login'])

if a.action=='stage':
    if (root/'activated.json').exists():raise SystemExit('Active installation cannot be restaged')
    if root.exists() and (not (root/'release').exists() or (root/'release').read_text().strip()!=a.release):raise SystemExit('Unowned target directory')
    if shutil.disk_usage('/').free<1_500_000_000:raise SystemExit('Insufficient disk headroom')
    run(['sha256sum','--check','SHA256SUMS'],cwd=payload)
    if not mysql('SELECT VERSION();',True).startswith('8.4.'):raise SystemExit('Unexpected shared MySQL version')
    existing=mysql("SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='mautic_cronfig';",True)
    if existing!='0':raise SystemExit('Target schema already exists; preserve it and inspect before retry')
    root.mkdir(parents=True,exist_ok=True);(root/'release').write_text(a.release+'\n')
    for name in ['config','media','plugins','themes']:
        shutil.copytree(payload/name,root/name,dirs_exist_ok=True)
    (root/'logs').mkdir(exist_ok=True)
    shutil.copytree(repo/'deployment/cronfig',root/'runtime',dirs_exist_ok=True)
    for name in ['config','media','logs']:
        run(['chown','-R','33:33',str(root/name)])
    run(['chmod','750',str(root/'config')]);run(['chmod','640',str(root/'config/local.php')])
    run(['openssl','x509','-checkend','86400','-noout','-in','/etc/letsencrypt/live/m.cronfig.io/fullchain.pem'])
    pw=(payload/'database-password').read_text().strip()
    Path('/etc/mautic').mkdir(mode=0o700,exist_ok=True)
    credential=Path('/etc/mautic/cronfig-database-password');credential.write_text(pw+'\n');credential.chmod(0o600)
    if not re.fullmatch('[a-f0-9]{48}',pw):raise SystemExit('Invalid database credential format')
    mysql(f"CREATE DATABASE `{schema}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER '{schema}'@'%' IDENTIFIED BY '{pw}'; GRANT ALL ON `{schema}`.* TO '{schema}'@'%';",True)
    import gzip
    with gzip.open(payload/'database.sql.gz','rb') as source:
        proc=subprocess.Popen(['docker','exec','-i','-e','MYSQL_PWD='+pw,'mautic_db','mysql','--no-defaults','-h127.0.0.1','-u'+schema,schema],stdin=subprocess.PIPE)
        shutil.copyfileobj(source,proc.stdin);proc.stdin.close()
        if proc.wait():raise RuntimeError('Schema-scoped import failed')
    networks=capture(['docker','network','ls','--format','{{.Name}}']).splitlines()
    if 'mautic-db-cronfig' not in networks:run(['docker','network','create','--internal','mautic-db-cronfig'])
    network=json.loads(capture(['docker','network','inspect','mautic-db-cronfig']))[0]
    if not network['Internal']:raise SystemExit('Database network is not internal')
    db=json.loads(capture(['docker','inspect','mautic_db']))[0]
    if 'mautic-db-cronfig' not in db['NetworkSettings']['Networks']:run(['docker','network','connect','--alias','mysql','mautic-db-cronfig','mautic_db'])
    run(compose(False)+['up','-d']);healthy()
    expected=json.loads((payload/'expected-counts.json').read_text())
    for table,count in expected.items():
        if table not in ['mautic_leads','mautic_form_submissions','mautic_email_stats']:raise SystemExit('Unexpected validation table')
        if int(mysql('SELECT COUNT(*) FROM '+table+';'))!=count:raise RuntimeError('Record count mismatch')
    nginx(False)
    (root/'staged.json').write_text(json.dumps({'release':a.release,'verified':True})+'\n')
    print('Cronfig staged in isolated network; original source and existing sites preserved.')
elif a.action=='activate':
    if not (root/'release').exists() or (root/'release').read_text().strip()!=a.release:raise SystemExit('Release ownership mismatch')
    shutil.copytree(repo/'deployment/cronfig',root/'runtime',dirs_exist_ok=True)
    if 'return 503;' not in Path('/etc/nginx/sites-available/m.cronfig.io').read_text():raise SystemExit('Hostname must be in maintenance before activation or retry')
    if not (root/'staged.json').exists():raise SystemExit('No verified stage')
    proof=json.loads((payload/'source-frozen.json').read_text())
    if proof.get('database_matches_rehearsal') is not True or proof.get('files_match_rehearsal') is not True:raise SystemExit('Final frozen source verification missing')
    # Retry preserves the imported database; no data is restored or reimported.
    shutil.copyfile(payload/'config/local.php',root/'config/local.php');run(['chown','33:33',str(root/'config/local.php')]);run(['chmod','640',str(root/'config/local.php')])
    # Outbound network is added while null mail and empty Cronfig keys remain active.
    run(compose(True)+['up','-d','--force-recreate']);healthy()
    try:
        shutil.copyfile(payload/'local.live.php',root/'config/local.php');run(['chown','33:33',str(root/'config/local.php')]);run(['chmod','640',str(root/'config/local.php')])
        run(compose(True)+['up','-d','--force-recreate']);healthy()
        nginx(True)
        # From this point the new database may contain writes: never auto-restore it.
        (root/'activated.json').write_text(json.dumps({'release':a.release,'time':time.time()})+'\n')
        # nginx reload is asynchronous; old workers may briefly return maintenance.
        for attempt in range(15):
            status=capture(['curl','-sS','--max-time','30','--resolve','m.cronfig.io:443:127.0.0.1','https://m.cronfig.io/s/login','-o','/dev/null','-w','%{http_code}'])
            if status=='200':break
            time.sleep(1)
        else:raise RuntimeError('Public HTTPS proxy returned HTTP '+status)
    except Exception:
        nginx(False)
        raise
    run(['python3',str(root/'runtime/backup.py')])
    Path('/etc/cron.d/mautic-cronfig-backup').write_text('17 3 * * * root python3 /opt/mautic/cronfig/runtime/backup.py >> /root/mautic-cronfig-backups/cron.log 2>&1\n')
    print('Cronfig application activated; private daily backups installed; DNS may now move to this server.')
elif a.action=='maintenance':
    nginx(False);print('Only m.cronfig.io is in maintenance; all data preserved.')
elif a.action=='renew-certificate':
    run(['certbot','certonly','--webroot','-w','/var/www/letsencrypt','-d','m.cronfig.io','--cert-name','m.cronfig.io','--non-interactive','--agree-tos','--register-unsafely-without-email','--force-renewal'])
    nginx((root/'activated.json').exists())
else:
    healthy();print('Cronfig and existing Veetr login checks passed.')
