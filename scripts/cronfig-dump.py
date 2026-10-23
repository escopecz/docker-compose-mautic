#!/usr/bin/env python3
"""Validate the reviewed Cronfig dump and scope its single legacy routine."""
import argparse,gzip,re
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source');p.add_argument('destination')
a=p.parse_args();routines=0
with gzip.open(a.source,'rt') as source,gzip.open(a.destination,'wt') as destination:
    for line in source:
        if line.startswith('CREATE DEFINER='):
            if not re.fullmatch(r'CREATE DEFINER=`root`@`%` PROCEDURE `mautic_cleanup`\(\)\n',line):
                raise SystemExit('Unreviewed routine/definer')
            line='CREATE PROCEDURE `mautic_cleanup`() SQL SECURITY INVOKER\n';routines+=1
        elif 'DEFINER=' in line and not line.startswith('INSERT INTO'):
            raise SystemExit('Unreviewed definer')
        if re.match(r'^(CREATE DATABASE|USE |CREATE USER|GRANT |REVOKE |DROP DATABASE)',line):
            raise SystemExit('Cross-schema/global statement rejected')
        if not line.startswith('INSERT INTO') and re.search(r'\bCREATE\b.*\bEVENT\b',line):
            raise SystemExit('Scheduled events require separate review')
        destination.write(line)
if routines!=1:raise SystemExit('Expected exactly one reviewed legacy routine')
print('Dump validated; legacy cleanup routine uses invoker rights.')
