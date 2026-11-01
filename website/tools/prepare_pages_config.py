#!/usr/bin/env python3
"""Apply GitHub Pages metadata to a build checkout, leaving local preview safe."""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

SOURCE_CONFIG = Path(__file__).resolve().parents[1] / '_config.yml'


def prepare_config(text, origin, base_path, repository):
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('Pages origin must be an HTTPS origin without a path or credentials')
    origin = origin.rstrip('/')
    base_path = base_path.rstrip('/')
    if base_path and (not re.fullmatch(r'/[A-Za-z0-9_./-]+', base_path)
                      or '//' in base_path or any(p in ('.', '..') for p in base_path.split('/'))):
        raise ValueError('Pages base path must be empty or a normal project path')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Pages repository must be owner/name')
    for key, value in {'url': origin, 'baseurl': base_path, 'repository': repository}.items():
        pattern = re.compile(r'^' + key + r'[ \t]*:.*$', re.MULTILINE)
        if len(pattern.findall(text)) > 1:
            raise ValueError('Duplicate top-level config key: ' + key)
        line = key + ': ' + json.dumps(value)
        if pattern.search(text):
            text = pattern.sub(lambda _: line, text)
        else:
            text = text.rstrip('\n') + '\n' + line + '\n'
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=SOURCE_CONFIG,
                        help='Build config copy; live source config is allowed only inside Actions')
    args = parser.parse_args()
    if args.config.resolve() == SOURCE_CONFIG and os.environ.get('GITHUB_ACTIONS') != 'true':
        parser.error('Refusing to change the local site config; use --config with a temporary copy')
    required = ('PAGES_ORIGIN', 'PAGES_BASE_PATH', 'PAGES_REPOSITORY')
    missing = [key for key in required if key not in os.environ]
    if missing:
        parser.error('Missing Pages metadata: ' + ', '.join(missing))
    try:
        result = prepare_config(args.config.read_text(encoding='utf-8-sig'),
                                *(os.environ[key] for key in required))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.config.write_text(result, encoding='utf-8')
    print('Prepared Pages build for ' + os.environ['PAGES_ORIGIN'].rstrip('/')
          + os.environ['PAGES_BASE_PATH'].rstrip('/') + '/')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
