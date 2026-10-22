import json, os, sys
source, target, run = sys.argv[1:]
c = json.load(open(source))
assert c['name'] == 'www'
for service in ('mautic', 'mautic_cron', 'mautic_worker'):
    if service not in c['services']:
        continue
    c['services'][service]['image'] = os.environ['TARGET_IMAGE']
    c['services'][service]['environment']['DOCKER_MAUTIC_RUN_MIGRATIONS'] = 'false'
c['services']['mautic']['ports'] = [{'target': 80, 'published': '8001', 'host_ip': '127.0.0.1', 'protocol': 'tcp'}]
c['services']['db']['image'] = os.environ['MYSQL_IMAGE']
command = c['services']['db'].get('command', [])
assert isinstance(command, list)
remaining = [x for x in command if not x.startswith('--default-authentication-plugin=')]
if remaining:
    c['services']['db']['command'] = remaining
else:
    c['services']['db'].pop('command', None)
for original, part in [('mautic_data','data'), ('mautic_config','config'), ('mautic_media','media'), ('mysql_data','mysql')]:
    assert c['volumes'][original]['name'] == 'www_' + original
    c['volumes'][original] = {'name': f'www_m7_{run}_{part}', 'external': True}
with open(target, 'w') as stream:
    json.dump(c, stream, indent=2)
