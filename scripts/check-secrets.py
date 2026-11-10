#!/usr/bin/env python3
"""Scan public Git candidates without printing matching values or reading ignored files."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


PATTERNS = {
    'private key': re.compile(r'-{5}BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-{5}'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,255}|github_pat_[A-Za-z0-9_]{30,255})\b'),
    'service token': re.compile(r'\b(?:xox[baprs]-[A-Za-z0-9-]{20,}|sk_(?:live|test)_[A-Za-z0-9]{20,}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,})\b'),
    'credential assignment': re.compile(r'''(?i)\b[A-Za-z0-9_]*(?:password|token|api[_-]?key|secret)[A-Za-z0-9_]*\s*[=:]\s*["'][A-Za-z0-9_+/=-]{24,}["']'''),
    'URL credentials': re.compile(r'https?://[^\s/:@]+:[^\s/@]+@'),
    'personal home path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/'),
}
PRIVATE_NAMES = {'.env', '.netrc', '.npmrc', 'config.local.sh', '.zshrc.local', '.wezterm.local.lua',
                 'auth.json', 'trust.json', 'credentials', 'credentials.json', 'id_rsa', 'id_ed25519', 'id_ecdsa'}
PRIVATE_DIRS = {'.ssh', '.aws', '.pi', '.agents', '.claude', '.codex', '__pycache__'}


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def inspect(label, path, data):
    findings = []
    if path:
        name = Path(path).name
        private = name in PRIVATE_NAMES or name.startswith('.env.') and name != '.env.example'
        private = private or bool(PRIVATE_DIRS.intersection(Path(path).parts))
        private = private or name.endswith(('.pem', '.key', '.p12', '.pfx', '.bak', '.log', '.pyc')) or '.bak.' in name
        private = private or name.startswith('config.local.sh.') and name != 'config.local.sh.example'
        if private:
            findings.append(f'{label}: private file must not be published')
        if name.endswith(('.zip', '.tar', '.gz', '.xz', '.tgz', '.dmg', '.pkg', '.bundle')) or any(part.endswith('.app') for part in Path(path).parts):
            findings.append(f'{label}: archive/installer contents require a separate review')
        for kind, pattern in PATTERNS.items():
            if pattern.search(path):
                findings.append(f'{label}: possible {kind} in filename')
    text = data.decode('utf-8', errors='replace')
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count('\n', 0, match.start()) + 1
            findings.append(f'{label}:{line}: possible {kind}')
    return findings


def scan(repo, history=True):
    repo = Path(repo).resolve()
    git(repo, 'rev-parse', '--show-toplevel')
    findings = []
    paths = set(git(repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0'))
    for raw in sorted(paths - {b''}):
        name = os.fsdecode(raw)
        path = repo / name
        label = f'working tree {name!r}'
        # Never follow a replaced parent directory into private files outside the repo.
        if os.path.commonpath([str(repo), str(path.parent.resolve())]) != str(repo):
            findings.append(f'{label}: parent points outside repository')
            continue
        if path.is_symlink():
            data = os.fsencode(os.readlink(path))
        elif path.is_file():
            data = path.read_bytes()
        else:
            continue
        findings.extend(inspect(label, name, data))

    for entry in git(repo, 'ls-files', '--stage', '-z').split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, oid, stage = metadata.split()
        if mode == b'160000':
            findings.append('index: submodule needs a separate public-content review')
            continue
        name = os.fsdecode(raw_name)
        data = git(repo, 'cat-file', 'blob', oid.decode())
        findings.extend(inspect(f'index {name!r}', name, data))

    if history:
        for entry in git(repo, 'rev-list', '--objects', '--all').splitlines():
            raw_oid, _, raw_name = entry.partition(b' ')
            oid = raw_oid.decode()
            kind = git(repo, 'cat-file', '-t', oid).strip()
            if kind not in (b'blob', b'commit'):
                continue
            name = os.fsdecode(raw_name) if raw_name else None
            label = f'history {oid[:12]} {name!r}'
            findings.extend(inspect(label, name, git(repo, 'cat-file', kind.decode(), oid)))
    return sorted(set(findings))


def history_contacts(repo):
    if not git(repo, 'rev-list', '--all').strip():
        return 0
    emails = set(git(repo, 'log', '--all', '--format=%ae%n%ce').decode().splitlines())
    known = {'noreply@github.com', 'web-flow@github.com'}
    return len({email for email in emails if email and email not in known and
                'noreply' not in email.lower() and not email.endswith('@example.com')})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--no-history', action='store_true', help='Scan working tree and index only')
    args = parser.parse_args()
    findings = scan(args.repo, history=not args.no_history)
    if not args.no_history:
        contacts = history_contacts(args.repo)
        if contacts:
            print(f'⚠️ Available history has {contacts} contact address(es) needing a publication privacy decision; values withheld.')
    if findings:
        for finding in findings:
            # Filenames can contain credentials too; redact those before reporting locations.
            for pattern in PATTERNS.values():
                finding = pattern.sub('[redacted]', finding)
            print(f'❌ {finding}')
        print('Matching values were withheld. Remove/revoke exposed credentials before publishing.')
        return 1
    print('✅ No findings in public Git candidates, index, or the requested available history.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.SubprocessError, ValueError):
        print('❌ Secret scan could not finish; check Git access and repository state.', file=sys.stderr)
        sys.exit(2)
