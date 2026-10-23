#!/usr/bin/env python3
"""Convert retained M4 themes to the namespaced Twig template paths used by M7."""
import argparse
from pathlib import Path


def convert(root):
    changed = 0
    for name in ('Mauve', 'coffee', 'nature'):
        for path in (root / name / 'html').glob('*.twig'):
            if path.name.startswith('._'):
                continue
            before = path.read_text()
            after = before
            for quote in ('"', "'"):
                after = after.replace(quote + ':' + name + ':base.html.twig' + quote,
                                      quote + '@themes/' + name + '/html/base.html.twig' + quote)
            if after != before:
                path.write_text(after)
                changed += 1
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('themes', type=Path)
    args = parser.parse_args()
    print(f'Updated {convert(args.themes)} legacy theme templates.')
