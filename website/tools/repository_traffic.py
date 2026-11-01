#!/usr/bin/env python3
"""Merge rolling GitHub traffic into a durable daily ledger; never commit or push."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ARTIFACT = 'logscience-repository-traffic-ledger'
MAX_BYTES = 1024 * 1024
MAX_COUNT = 2**53 - 1
ROOT = Path(__file__).resolve().parents[1]


def count(value):
    if type(value) is not int or not 0 <= value <= MAX_COUNT:
        raise ValueError('Traffic counts must be non-negative safe integers')
    return value


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r'20\d\d-\d\d-\d\d', value):
        raise ValueError('Invalid UTC day')
    return date.fromisoformat(value)


def validate_state(repository, state):
    if (state.get('schema') != 1 or state.get('repository') != repository
            or state.get('metric') != 'repository_page_views'):
        raise ValueError('Foreign repository or invalid traffic ledger')
    start = day(state.get('coverage_start'))
    days = state.get('days')
    if not isinstance(days, dict) or not days:
        raise ValueError('Traffic ledger must contain daily observations')
    for key, value in days.items():
        if day(key) < start:
            raise ValueError('Ledger contains data before its declared scope')
        count(value)
    observed = count(sum(days.values()))
    if 'total' in state and count(state['total']) != observed:
        raise ValueError('Ledger total does not match daily counts')
    return start, days


def merge_reports(repository, states, snapshot, as_of=None):
    if not states:
        raise ValueError('A verified starting ledger is required')
    start, _ = validate_state(repository, states[0])
    days = {}
    for state in states:
        scope, records = validate_state(repository, state)
        if scope != start:
            raise ValueError('Ledger coverage start changed')
        for key, value in records.items():
            days[key] = max(days.get(key, 0), value)
    incoming = {}
    for entry in snapshot.get('views', []):
        stamp = entry.get('timestamp', '')
        if not re.fullmatch(r'20\d\d-\d\d-\d\dT00:00:00Z', stamp):
            raise ValueError('Traffic timestamps must use UTC midnight')
        key = stamp[:10]
        day(key)
        if key in incoming:
            raise ValueError('Duplicate day in traffic report')
        incoming[key] = count(entry.get('count'))
    if (not incoming and as_of is None) or count(snapshot.get('count')) != sum(incoming.values()):
        raise ValueError('Traffic snapshot has no days or an inconsistent total')
    # The API may omit zero-traffic days. Only infer zeros inside a known
    # rolling window; never bridge a missed older window with invented data.
    if as_of is not None:
        if type(as_of) is not date or any(day(key) > as_of for key in incoming):
            raise ValueError('Invalid snapshot collection day')
        for offset in range(14):
            key = (as_of - timedelta(days=offset)).isoformat()
            incoming.setdefault(key, 0)
    for key, value in incoming.items():
        if day(key) >= start:
            days[key] = max(days.get(key, 0), value)
    end = max(day(key) for key in days)
    current = start
    while current <= end:
        if current.isoformat() not in days:
            raise ValueError('Missing repository traffic day: ' + current.isoformat())
        current += timedelta(days=1)
    return {'schema':1, 'repository':repository, 'metric':'repository_page_views',
            'coverage_start':start.isoformat(), 'days':dict(sorted(days.items())),
            'total':count(sum(days.values()))}


def update_config(config, ledger):
    result = dict(config)
    result['repository_views'] = ledger['total']
    result['repository_updated_on'] = max(ledger['days'])
    return result


def recovery_states(repository, seed, restored_path, restored_ok, deployed):
    states, warnings = [seed], []
    scope, _ = validate_state(repository, seed)
    candidates = []
    if restored_ok and restored_path.exists():
        try:
            candidates.append(('artifact', json.loads(restored_path.read_text(encoding='utf-8'))))
        except (OSError, ValueError):
            warnings.append('Artifact ledger unavailable or incomplete; trying deployed recovery data')
    if deployed is not None:
        candidates.append(('deployed', deployed))
    for source, state in candidates:
        try:
            recovered_scope, _ = validate_state(repository, state)
            if recovered_scope != scope:
                raise ValueError('Different scope')
        except (ValueError, TypeError, AttributeError):
            warnings.append('Ignored invalid ' + source + ' traffic ledger')
        else:
            states.append(state)
    return states, warnings


def select_artifact(records, repository_id):
    candidates = [item for item in records
                  if item.get('name') == ARTIFACT and not item.get('expired')
                  and 0 < item.get('size_in_bytes', 0) < MAX_BYTES
                  and item.get('workflow_run', {}).get('head_branch') == 'master'
                  and item.get('workflow_run', {}).get('head_repository_id') == repository_id]
    return max(candidates, key=lambda item:item['id']) if candidates else None


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def read_json(url, token=None, allow_missing=False):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Only credential-free HTTPS resource URLs are allowed')
    if token and parsed.netloc != 'api.github.com':
        raise ValueError('GitHub token is restricted to api.github.com')
    headers = {'User-Agent':'LogScience-traffic-sync', 'Accept':'application/vnd.github+json'}
    if token:
        headers.update(Authorization='Bearer ' + token, **{'X-GitHub-Api-Version':'2022-11-28'})
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404 and allow_missing:
            return None
        raise ValueError('Traffic resource returned HTTP ' + str(error.code)) from None
    if len(raw) > MAX_BYTES:
        raise ValueError('Traffic resource exceeded size limit')
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['find-artifact', 'collect'])
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        parser.error('Network collection and build mutation run only inside GitHub Actions')
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        parser.error('Invalid repository metadata')
    try:
        if args.command == 'find-artifact':
            token = os.environ.get('GITHUB_TOKEN')
            if not token:
                raise ValueError('Missing ephemeral Actions read token')
            listing = read_json('https://api.github.com/repos/' + repository
                                + '/actions/artifacts?name=' + ARTIFACT + '&per_page=30', token)
            selected = select_artifact(listing.get('artifacts', []), int(os.environ['GITHUB_REPOSITORY_ID']))
            print('artifact_id=' + str(selected['id'] if selected else ''))
            print('run_id=' + str(selected['workflow_run']['id'] if selected else ''))
            return 0

        token = os.environ.get('TRAFFIC_READ_TOKEN')
        if not token:
            raise ValueError('Set TRAFFIC_READ_TOKEN as an Actions secret with Administration:read for this repository')
        seed = json.loads((ROOT / '_data/repository_traffic_seed.json').read_text(encoding='utf-8'))
        state_file = ROOT / 'local/traffic-state/ledger.json'
        origin = os.environ['PAGES_ORIGIN'].rstrip('/')
        base_path = os.environ['PAGES_BASE_PATH'].rstrip('/')
        parsed = urlsplit(origin)
        if (parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.github.io')
                or parsed.netloc != parsed.hostname or parsed.path or parsed.query or parsed.fragment
                or not re.fullmatch(r'(?:/[A-Za-z0-9_.-]+)*', base_path)):
            raise ValueError('Unrecognized Pages recovery address')
        try:
            deployed = read_json(origin + base_path + '/metrics/repository-traffic.json', allow_missing=True)
        except (ValueError, OSError):
            deployed = None
            print('::warning::Deployed traffic recovery data unavailable; trying artifact or seed')
        states, warnings = recovery_states(repository, seed, state_file,
                         os.environ.get('TRAFFIC_RESTORE_OUTCOME') == 'success', deployed)
        for warning in warnings:
            print('::warning::' + warning)
        snapshot = read_json('https://api.github.com/repos/' + repository + '/traffic/views?per=day', token)
        ledger = merge_reports(repository, states, snapshot, as_of=datetime.now(timezone.utc).date())
        ledger['last_fetched_at'] = datetime.now(timezone.utc).isoformat()
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(ledger, indent=2) + '\n', encoding='utf-8')
        config_file = ROOT / '_data/page_views.json'
        config = update_config(json.loads(config_file.read_text(encoding='utf-8')), ledger)
        config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Repository views: ' + str(ledger['total']) + '; observed UTC days: ' + str(len(ledger['days'])))
        return 0
    except (ValueError, KeyError, OSError) as error:
        # Never print HTTP bodies, request headers or environment values.
        parser.exit(1, 'Traffic sync failed: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
