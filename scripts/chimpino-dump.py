#!/usr/bin/env python3
"""Validate the Chimpino dump before its schema-scoped import."""
import argparse,gzip,re
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source');p.add_argument('destination')
a=p.parse_args()
with gzip.open(a.source,'rt') as source,gzip.open(a.destination,'wt') as destination:
    for line in source:
        if 'DEFINER=' in line and not line.startswith('INSERT INTO'):
            raise SystemExit('Unreviewed definer')
        if re.match(r'^(CREATE DATABASE|USE |CREATE USER|GRANT |REVOKE |DROP DATABASE)',line):
            raise SystemExit('Cross-schema/global statement rejected')
        if not line.startswith('INSERT INTO') and re.search(r'\bCREATE\b.*\b(EVENT|PROCEDURE|FUNCTION)\b',line):
            raise SystemExit('Stored programs require separate review')
        destination.write(line)
print('Chimpino dump validated; no routines, definers, events or global statements.')
