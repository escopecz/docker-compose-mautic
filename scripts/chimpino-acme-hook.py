#!/usr/bin/env python3
"""Expose only the public ACME challenge, keeping the TLS private key on the server."""
import json,os,subprocess,time
from pathlib import Path
if os.environ['CERTBOT_DOMAIN']!='m.chimpino.com':raise SystemExit('Unexpected certificate domain')
value=os.environ['CERTBOT_VALIDATION']
p=Path('/root/chimpino-acme-pending.json');p.write_text(json.dumps({'name':'_acme-challenge.m','value':value}));p.chmod(0o600)
for _ in range(90):
    results=[subprocess.check_output(['dig','+short','TXT','_acme-challenge.m.chimpino.com','@'+ns],text=True) for ns in ['ns47.domaincontrol.com','ns48.domaincontrol.com']]
    if all(value in r for r in results):time.sleep(20);break
    time.sleep(5)
else:raise SystemExit('ACME DNS challenge did not propagate')
