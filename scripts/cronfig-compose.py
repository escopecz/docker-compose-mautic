#!/usr/bin/env python3
"""Render the scoped Cronfig stack; shared MySQL is managed independently."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--root',default='/opt/mautic/cronfig')
p.add_argument('--live',action='store_true')
p.add_argument('--local',action='store_true')
a=p.parse_args()
r=str(Path(a.root).resolve())
image=json.loads((Path(__file__).resolve().parents[1]/'instances/cronfig.json').read_text())['image']
mounts=[f'{r}/config:/var/www/html/config',f'{r}/media/files:/var/www/html/docroot/media/files',f'{r}/media/images:/var/www/html/docroot/media/images',f'{r}/logs:/var/www/html/var/logs',f'{r}/plugins/CronfigBundle:/var/www/html/docroot/plugins/CronfigBundle:ro',f'{r}/runtime/entrypoint.sh:/opt/cronfig-entrypoint.sh:ro',f'{r}/runtime/apache-workers.conf:/etc/apache2/conf-enabled/zz-cronfig-workers.conf:ro',f'{r}/runtime/php.ini:/usr/local/etc/php/conf.d/zz-cronfig.ini:ro']
for name in ('coffee','nature','Mauve'):
    mounts.append(f'{r}/themes/{name}:/var/www/html/docroot/themes/{name}:ro')
net='cronfig-prod-rehearsal' if a.local else 'mautic-db-cronfig'
networks={'database':{'external':True,'name':net}}
if a.live:networks['outbound']={'name':'mautic-cronfig-outbound'}
web={'image':image,'platform':'linux/amd64','container_name':'cronfig-production-rehearsal' if a.local else 'mautic-cronfig-web','restart':'unless-stopped','entrypoint':['/opt/cronfig-entrypoint.sh'],'environment':{'APP_ENV':'prod','APP_DEBUG':'0','MAUTIC_TABLE_PREFIX':'mautic_'},'ports':[f'127.0.0.1:{8192 if a.local else 8002}:80'],'volumes':mounts,'networks':list(networks),'mem_limit':'320m','cpus':0.75,'logging':{'driver':'json-file','options':{'max-size':'10m','max-file':'3'}},'healthcheck':{'test':['CMD-SHELL','test "$$(curl -sS -H \'Host: m.cronfig.io\' -H \'X-Forwarded-Proto: https\' -o /dev/null -w \'%{http_code}\' http://127.0.0.1/s/login)" = 200'],'interval':'30s','timeout':'10s','start_period':'60s','retries':3}}
print(json.dumps({'name':'cronfig-image-rehearsal' if a.local else 'mautic-cronfig','services':{'web':web},'networks':networks},indent=2))
