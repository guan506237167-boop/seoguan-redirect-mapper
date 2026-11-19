"""Check a proposed migration mapping offline; no server mutations."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def valid_url(value):
    try:
        p = urlsplit(value)
        _ = p.port
        return p.scheme in ('http', 'https') and bool(p.hostname) and not p.username and not p.password and not any(c.isspace() or ord(c) < 32 for c in value)
    except ValueError:
        return False


def identity_url(value):
    """Normalize network identity only; preserve original rows in the report."""
    p = urlsplit(value)
    host = p.hostname.lower()
    host = '[' + host + ']' if ':' in host else host.encode('idna').decode('ascii')
    if p.port is not None and p.port != (443 if p.scheme == 'https' else 80):
        host += ':' + str(p.port)
    return urlunsplit((p.scheme, host, p.path or '/', p.query, p.fragment))


def audit(rows, inventory=None):
    graph = defaultdict(set)
    destinations = defaultdict(set)
    issues = []
    pairs = set()
    original_rows = []
    for line, row in enumerate(rows, 2):
        old, new = (row.get('old_url') or '').strip(), (row.get('new_url') or '').strip()
        if not valid_url(old) or not valid_url(new):
            issues.append({'type': 'invalid_url', 'line': line, 'old_url': old, 'new_url': new})
            continue
        raw_old, raw_new = old, new
        try:
            old, new = identity_url(old), identity_url(new)
        except UnicodeError:
            issues.append({'type': 'invalid_hostname', 'line': line, 'old_url': raw_old, 'new_url': raw_new})
            continue
        original_rows.append({'line': line, 'old_url': raw_old, 'new_url': raw_new,
                              'normalized_old_url': old, 'normalized_new_url': new})
        if (old, new) in pairs:
            issues.append({'type': 'duplicate_row', 'line': line, 'old_url': old, 'new_url': new})
        pairs.add((old, new))
        graph[old].add(new)
        destinations[new].add(old)
        if old == new:
            issues.append({'type': 'self_mapping', 'old_url': old})
    for old, targets in graph.items():
        if len(targets) > 1:
            issues.append({'type': 'conflicting_targets', 'old_url': old, 'targets': sorted(targets)})
    for new, sources in destinations.items():
        if len(sources) > 1:
            issues.append({'type': 'many_to_one_review', 'new_url': new, 'sources': sorted(sources)})
    # Follow only unambiguous edges. Conflicting branches are reported above.
    completed = set()
    for start in graph:
        if len(graph[start]) == 1:
            target = next(iter(graph[start]))
            if target in graph and target != start:
                issues.append({'type': 'redirect_chain', 'old_url': start, 'intermediate': target})
        if start in completed:
            continue
        path, positions, current = [], {}, start
        while current in graph and len(graph[current]) == 1 and current not in completed:
            if current in positions:
                cycle = path[positions[current]:]
                if len(cycle) > 1:
                    issues.append({'type': 'cycle', 'urls': cycle + [current]})
                break
            positions[current] = len(path)
            path.append(current)
            target = next(iter(graph[current]))
            current = target
        completed.update(path)
    if inventory is not None:
        for old in sorted(set(v.strip() for v in inventory if v.strip())):
            if not valid_url(old):
                issues.append({'type': 'invalid_inventory_url', 'old_url': old})
            elif identity_url(old) not in graph:
                issues.append({'type': 'unmapped_old_url', 'old_url': old})
    return {'counts': {'unique_pairs': len(pairs), 'old_urls': len(graph), 'issues': len(issues)},
            'issues': issues, 'original_rows': original_rows, 'inventory_checked': inventory is not None,
            'live_redirects_checked': False, 'destination_status': 'unverified'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--inventory', type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    try:
        with a.input.open(encoding='utf-8-sig', newline='') as f:
            r = csv.DictReader(f)
            if not {'old_url', 'new_url'}.issubset(r.fieldnames or []):
                raise ValueError('CSV requires old_url,new_url')
            result = audit(list(r), a.inventory.read_text(encoding='utf-8-sig').splitlines() if a.inventory else None)
        with a.output.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result['counts']))
    except (OSError, ValueError, csv.Error) as e:
        p.exit(2, str(e) + '\n')


if __name__ == '__main__':
    main()
