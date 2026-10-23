#!/usr/bin/env python3
"""Issue TLS on the destination; only public DNS challenges cross the SSH connection."""
import json,os,subprocess,time,urllib.request
host='165.232.83.73';sha=os.environ['GITHUB_SHA']
if len(sha)!=40 or any(c not in '0123456789abcdef' for c in sha):raise SystemExit('Invalid revision')
code='/root/cronfig-code-'+sha
exists=subprocess.run(['ssh',host,'test -s /etc/letsencrypt/live/m.cronfig.io/fullchain.pem']).returncode==0
if exists:print('Destination certificate already exists.');raise SystemExit(0)
subprocess.run(['ssh',host,'rm -f /root/cronfig-acme-pending.json'],check=True)
command=f"certbot certonly --manual --preferred-challenges dns --manual-auth-hook 'python3 {code}/scripts/cronfig-acme-hook.py' -d m.cronfig.io --cert-name m.cronfig.io --non-interactive --agree-tos --register-unsafely-without-email > /root/cronfig-certificate.log 2>&1"
proc=subprocess.Popen(['ssh',host,command],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
base='https://api.digitalocean.com/v2/domains/cronfig.io/records';record=None
try:
    for _ in range(60):
        r=subprocess.run(['ssh',host,'cat /root/cronfig-acme-pending.json'],capture_output=True,text=True)
        if r.returncode==0:pending=json.loads(r.stdout);break
        if proc.poll() is not None:raise RuntimeError('Certificate command failed; diagnostics stay on destination')
        time.sleep(2)
    else:raise RuntimeError('Certificate challenge not generated')
    if pending['name']!='_acme-challenge.m':raise RuntimeError('Unexpected DNS name')
    req=urllib.request.Request(base,data=json.dumps({'type':'TXT','name':pending['name'],'data':pending['value'],'ttl':60}).encode(),headers={'Authorization':'Bearer '+os.environ['DIGITALOCEAN_TOKEN'],'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=30) as r:record=json.load(r)['domain_record']['id']
    if proc.wait(timeout=600)!=0:raise RuntimeError('Certificate issuance failed; diagnostics stay on destination')
    print('New m.cronfig.io TLS certificate issued on destination; private key never transferred.')
finally:
    if record:
        req=urllib.request.Request(base+'/'+str(record),headers={'Authorization':'Bearer '+os.environ['DIGITALOCEAN_TOKEN']},method='DELETE')
        with urllib.request.urlopen(req,timeout=30):pass
