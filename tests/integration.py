#!/usr/bin/env python3
"""Disposable integration test: no production connections, files or credentials."""
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('render',ROOT/'scripts/render.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


with tempfile.TemporaryDirectory(prefix='mautic-example-test-') as tmp:
    temp=Path(tmp);items=m.inventory(ROOT/'instances.example.json')
    for i in items:i['port']=port()
    m.initialize(items,temp/'secrets')
    config=m.render(items)
    # Test databases cannot reach external services; application network is also isolated.
    for network in config['networks'].values():network['internal']=True
    for secret in config['secrets'].values():secret['file']=str(temp/'secrets'/Path(secret['file']).name)
    for service in config['services'].values():
        service.pop('build',None)
        service['restart']='no'
        service['volumes']=[str(ROOT/v[2:]) if v.startswith('./runtime:') or v.startswith('./runtime/') else v for v in service.get('volumes',[])]
    composefile=temp/'compose.json';composefile.write_text(json.dumps(config))
    project='mautic-test-'+uuid.uuid4().hex[:10]
    cmd=['docker','compose','-p',project,'-f',str(composefile)]
    def run(*args,**kwargs):return subprocess.run(cmd+list(args),check=True,**kwargs)
    def query(schema,sql,check=True):
        return subprocess.run(cmd+['exec','-T','db','bash','/opt/example/database-client.sh','query',schema],input=sql,text=True,capture_output=True,check=check)
    try:
        run('up','-d','db')
        for _ in range(120):
            result=query('mautic_marketing','SELECT 1;',False)
            if result.returncode==0:break
            state=subprocess.check_output(cmd+['ps','-a','--format','{{.State}}','db'],text=True).strip()
            if state == 'exited':
                run('logs','--tail','80','db')
                raise RuntimeError('Test database exited during startup')
            time.sleep(2)
        else:
            run('logs','--tail','80','db')
            raise RuntimeError('Test database startup failed')
        assert query('mautic_marketing','SELECT @@event_scheduler;').stdout.strip()=='DISABLED'
        query('mautic_sales','CREATE TABLE private_data (id INT);')
        denied=query('mautic_marketing','SELECT * FROM mautic_sales.private_data;',False)
        assert denied.returncode!=0 and 'denied' in denied.stderr.lower(),denied.stderr
        # An underscore in a GRANT must not become a wildcard for other schemas.
        run('exec','-T','db','bash','-c',
            'export MYSQL_PWD="$(cat /run/mysql-secrets/mysql_root_password)"; exec mysql --no-defaults -uroot',
            input='CREATE DATABASE mauticXmarketing; CREATE TABLE mauticXmarketing.private_data (id INT);',text=True)
        wildcard=query('mautic_marketing','SELECT * FROM mauticXmarketing.private_data;',False)
        assert wildcard.returncode!=0 and 'denied' in wildcard.stderr.lower(),wildcard.stderr
        marker='/tmp/mautic-shell-marker'
        for payload in ('\\! touch '+marker+'\n', 'system touch '+marker+'\n', '/*! \\! touch '+marker+' */;\n'):
            result=subprocess.run(cmd+['exec','-T','db','bash','/opt/example/database-client.sh','import','mautic_marketing'],input=payload,text=True,capture_output=True)
            assert result.returncode!=0,'Unsafe client command was accepted'
            run('exec','-T','db','test','!','-e',marker)
        query('mautic_marketing','CREATE TABLE event_probe (id INT); CREATE EVENT test_event ON SCHEDULE EVERY 1 SECOND DO INSERT INTO event_probe VALUES (1);')
        time.sleep(3)
        assert query('mautic_marketing','SELECT COUNT(*) FROM event_probe;').stdout.strip()=='0'
        # Root credentials must not appear in client argv. Hold a dummy query briefly.
        slow=subprocess.Popen(cmd+['exec','-T','db','bash','/opt/example/database-client.sh','query','mautic_marketing'],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        slow.stdin.write('SELECT SLEEP(4);');slow.stdin.close();time.sleep(1)
        container=subprocess.check_output(cmd+['ps','-q','db'],text=True).strip()
        argv=subprocess.check_output(['docker','top',container,'-eo','pid,args'],text=True)
        for secret in (temp/'secrets').iterdir():assert secret.read_text().strip() not in argv
        assert slow.wait()==0
        run('up','-d','marketing-web')
        web_container=subprocess.check_output(cmd+['ps','-q','marketing-web'],text=True).strip()
        mounts=json.loads(subprocess.check_output(['docker','inspect','--format','{{json .Mounts}}',web_container],text=True))
        expected={v.split(':')[1]:project+'_'+v.split(':')[0] for v in config['services']['marketing-web']['volumes']}
        actual={mount['Destination']:mount['Name'] for mount in mounts if mount['Type']=='volume'}
        assert actual == expected, 'Unexpected anonymous volume could hide persistent application data'
        for _ in range(90):
            result=subprocess.run(cmd+['exec','-T','marketing-web','curl','--max-time','90','-sSL','-o','/dev/null','-w','%{http_code}','http://127.0.0.1/installer'],capture_output=True,text=True)
            if result.returncode==0 and result.stdout=='200':break
            time.sleep(2)
        else:raise RuntimeError('Mautic installer did not return HTTP 200')
        run('exec','-T','marketing-web','php','-r',"$m=json_decode(file_get_contents('/var/www/html/docroot/plugins/GrapesJsBuilderBundle/Assets/library/js/dist/manifest.json'),true); foreach(['builder.js','builder.css'] as $k) if(empty($m[$k]) || !is_file('/var/www/html/docroot/plugins/GrapesJsBuilderBundle/Assets/library/js/dist/'.$m[$k])) exit(1);")
        run('exec','-T','--user','www-data','marketing-web','php','/var/www/html/bin/console','mautic:install','http://localhost',
            '--admin_username=admin','--admin_password=Disposable-Test-Password-Only-123!',
            '--admin_email=admin@example.com','--admin_firstname=Test','--admin_lastname=User','--force','--no-interaction')
        response=subprocess.check_output(cmd+['exec','-T','marketing-web','curl','--max-time','90','-fsS','http://127.0.0.1/s/login'],text=True)
        assert '_username' in response
        run('--profile','jobs','up','-d','marketing-cron','marketing-worker')
        for _ in range(30):
            cron=subprocess.run(cmd+['exec','-T','marketing-cron','pgrep','-x','cron'],capture_output=True)
            worker=subprocess.run(cmd+['exec','-T','marketing-worker','pgrep','-f','messenger:consume'],capture_output=True)
            if cron.returncode==0 and worker.returncode==0:break
            time.sleep(2)
        else:raise RuntimeError('Cron or queue worker failed to start')
        # Exercise the real backup/rehearsal implementation using only test data.
        import sys,os
        sys.path.insert(0,str(ROOT/'scripts'))
        import backup as backup_module
        backup_module.ROOT=temp
        (temp/'runtime').symlink_to(ROOT/'runtime',target_is_directory=True)
        os.environ['COMPOSE_PROJECT_NAME']=project
        backup_module.backup('marketing',temp/'backup')
        backup_module.rehearse('marketing',temp/'backup')
        print('PASS: isolation, safe imports, disabled events, secret-free argv, installer, editor, jobs and backup/restore')
    finally:
        run('--profile','jobs','down','-v','--remove-orphans')
