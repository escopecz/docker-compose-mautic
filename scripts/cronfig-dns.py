#!/usr/bin/env python3
"""Move only the reviewed Cronfig Mautic A record after application activation."""
import json,os,urllib.request
base='https://api.digitalocean.com/v2/domains/cronfig.io/records'
def request(url,data=None):
    req=urllib.request.Request(url,data=json.dumps(data).encode() if data else None,headers={'Authorization':'Bearer '+os.environ['DIGITALOCEAN_TOKEN'],'Content-Type':'application/json'},method='PUT' if data else 'GET')
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
records=[];url=base+'?per_page=200'
while url:
    page=request(url);records.extend(page['domain_records']);url=page.get('links',{}).get('pages',{}).get('next')
targets=[r for r in records if r['name']=='m' and r['type']=='A']
conflicts=[r for r in records if r['name']=='m' and r['type'] in ['AAAA','CNAME']]
if len(targets)!=1 or conflicts:raise SystemExit('Unexpected DNS topology; no changes made')
r=targets[0]
if r['data'] not in ['165.22.37.83','165.232.83.73']:raise SystemExit('Unexpected source address; no changes made')
request(base+'/'+str(r['id']),{'data':'165.232.83.73','ttl':300})
verified=request(base+'/'+str(r['id']))['domain_record']
if verified['data']!='165.232.83.73':raise SystemExit('DNS update verification failed')
print('m.cronfig.io A record now points to the verified destination; TTL 300.')
