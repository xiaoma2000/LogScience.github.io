#!/usr/bin/env python3
"""Publish confirmed view counts with Pages; no credentials or source commits."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_COUNT = 2**53 - 1


def count(value):
    if type(value) is not int or not 0 <= value <= MAX_COUNT:
        raise ValueError('Invalid view count')
    return value


def timestamp(value, now):
    if not isinstance(value, str) or not re.fullmatch(r'20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z', value):
        raise ValueError('Invalid source timestamp')
    parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed > datetime.fromisoformat(now.replace('Z','+00:00')) + timedelta(minutes=5):
        raise ValueError('Future source timestamp')
    return parsed


def combine(config, previous, live, now):
    repository = count(config['repository_views'])
    website = count(config['website_views'])
    source_time = config['website_updated_at']
    source_date = timestamp(source_time, now)
    warnings = []
    if previous is not None:
        try:
            if previous.get('schema') != 1 or previous.get('site_code') != config['site_code']:
                raise ValueError('Foreign snapshot')
            old_repo, old_web = count(previous['repository_views']), count(previous['website_views'])
            if count(previous['total']) != count(old_repo + old_web):
                raise ValueError('Inconsistent total')
            stamp = previous['website_updated_at']
            parsed = timestamp(stamp, now)
            timestamp(previous['updated_at'], now)
            repository = max(repository, old_repo)
            if old_web > website or (old_web == website and parsed > source_date):
                website, source_time, source_date = old_web, stamp, parsed
        except (ValueError, TypeError, KeyError, AttributeError):
            warnings.append('Ignored invalid deployed view snapshot')
    if live is not None:
        try:
            fresh = count(live['count'])
            stamp = live['updated_at']
            parsed = timestamp(stamp, now)
            if fresh > website or (fresh == website and parsed > source_date):
                website, source_time = fresh, stamp
        except (ValueError, TypeError, KeyError):
            warnings.append('Ignored invalid fast-counter response')
    return {'schema':1, 'site_code':config['site_code'], 'repository_views':repository,
            'website_views':website, 'total':count(repository + website),
            'website_updated_at':source_time, 'updated_at':now}, warnings


def update_config(config, snapshot):
    result = dict(config)
    for field in ('repository_views','website_views','website_updated_at'):
        result[field] = snapshot[field]
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_json(url):
    request = urllib.request.Request(url, headers={'User-Agent':'LogScience-confirmed-views',
                                                  'Accept':'application/json','Cache-Control':'no-cache'})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError('Oversized view snapshot')
        return json.loads(raw)


def build(root, origin, base_path, reader=read_json, now=None):
    parsed = urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.github.io')
            or parsed.netloc != parsed.hostname or parsed.path or parsed.query or parsed.fragment
            or not re.fullmatch(r'(?:/[A-Za-z0-9_.-]+)*',base_path)):
        raise ValueError('Unrecognized Pages address')
    config_path = root / '_data/page_views.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    worker = urlsplit(config['counter_endpoint'])
    if (worker.scheme != 'https' or not worker.hostname or not worker.hostname.endswith('.workers.dev')
            or worker.netloc != worker.hostname or worker.path != '/views' or worker.query or worker.fragment):
        raise ValueError('Unrecognized fast-counter address')
    now = now or datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    recovered, live, warnings = None, None, []
    state_path = root / 'local/traffic-state/page-views.json'
    artifact = None
    if state_path.exists():
        try:
            artifact = json.loads(state_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            warnings.append('Restored view snapshot unavailable; trying deployed recovery data')
    try:
        recovered = reader(origin + base_path + '/metrics/page-views.json')
    except (OSError, ValueError):
        warnings.append('Deployed view snapshot unavailable; retaining verified source seed')
    try:
        live = reader(config['counter_endpoint'])
    except (OSError, ValueError):
        warnings.append('Fast counter unavailable; retaining last confirmed website count')
    recovered_ok = False
    for previous in (artifact,recovered):
        merged, issues = combine(config, previous, None, now)
        if previous is not None and not issues:
            recovered_ok = True
        warnings.extend(issues)
        config = update_config(config,merged)
    snapshot, validation_warnings = combine(config, None, live, now)
    if not recovered_ok and (live is None or validation_warnings):
        # Keep the last deployed website intact instead of successfully publishing
        # an old source seed after losing both durable recovery paths.
        raise ValueError('No valid view recovery or current counter; retaining the existing deployment')
    output = root / 'metrics/page-views.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(snapshot,indent=2) + '\n',encoding='utf-8')
    state_path.parent.mkdir(parents=True,exist_ok=True)
    state_path.write_text(json.dumps(snapshot,indent=2) + '\n',encoding='utf-8')
    config_path.write_text(json.dumps(update_config(config,snapshot),ensure_ascii=False,indent=2) + '\n',encoding='utf-8')
    return snapshot, warnings + validation_warnings


def main():
    snapshot, warnings = build(ROOT, os.environ['PAGES_ORIGIN'].rstrip('/'),
                               os.environ.get('PAGES_BASE_PATH','').rstrip('/'))
    for warning in warnings:
        print('::warning::' + warning)
    print('Confirmed combined views: ' + str(snapshot['total']))


if __name__ == '__main__':
    main()
