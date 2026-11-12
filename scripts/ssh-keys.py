#!/usr/bin/env python3
"""Prepare local SSH keys and register only public keys on confirmed GitHub accounts."""

import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request


class SetupError(Exception):
    pass


def key_name(value):
    reserved = {'config', 'known_hosts', 'known_hosts.old', 'authorized_keys', 'environment', 'rc'}
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}', value) or value.lower() in reserved or value.lower().endswith('.pub'):
        raise SetupError('SSH key names must be distinct, ordinary filenames, not SSH config files or .pub names.')
    return value


def github_user(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', value):
        raise SetupError('Enter a GitHub login, not a name, URL, or email address.')
    return value


def fingerprint(path, private=False):
    if private:
        # Prevent ssh-keygen from silently using an adjacent .pub instead of the private file.
        with tempfile.TemporaryDirectory(prefix='.dotfiles-verify-', dir=path.parent) as temporary:
            isolated = Path(temporary) / 'private'
            shutil.copyfile(path, isolated)
            isolated.chmod(0o600)
            return fingerprint(isolated)
    result = subprocess.run(['ssh-keygen', '-l', '-E', 'sha256', '-f', str(path)],
                            stdin=subprocess.DEVNULL, capture_output=True, text=True)
    fields = result.stdout.split()
    if result.returncode or len(fields) < 2 or not fields[1].startswith('SHA256:'):
        raise SetupError('An existing SSH key could not be verified; no key files were replaced.')
    return fields[1]


def public_material(path):
    lines = path.read_bytes().strip().splitlines()
    fields = lines[0].split() if len(lines) == 1 else []
    if len(fields) < 2 or not fields[0].startswith((b'ssh-', b'ecdsa-', b'sk-')):
        raise SetupError('Invalid SSH public key; inspect it locally.')
    try:
        base64.b64decode(fields[1], validate=True)
        material = b' '.join(fields[:2]).decode('ascii')
    except ValueError as error:
        raise SetupError('Invalid SSH public key encoding.') from error
    return material  # Never upload personal comments/hostnames from an old .pub file.


def ensure_key(directory, name, role, interactive):
    private = directory / key_name(name)
    public = directory / (name + '.pub')
    if private.is_symlink() or public.is_symlink() or any(path.exists() and not path.is_file() for path in (private, public)):
        raise SetupError('SSH key paths must be regular files, not directories or symlinks.')
    if public.exists() and not private.exists():
        raise SetupError('A public key exists without its private key; restore the private key or choose a new filename.')
    if not private.exists():
        if not interactive:
            raise SetupError('Missing keys require an interactive terminal for passphrase entry. Run dotfiles ssh-keys in a terminal.')
        print(f'🔒 Creating the {role} Ed25519 key; choose a non-empty passphrase in ssh-keygen.')
        with tempfile.TemporaryDirectory(prefix='.dotfiles-key-', dir=directory) as temporary:
            generated = Path(temporary) / 'key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-a', '100', '-C', 'dotfiles-' + role,
                            '-f', str(generated)], stdout=subprocess.DEVNULL, check=True)
            if fingerprint(generated, private=True) != fingerprint(Path(str(generated) + '.pub')):
                raise SetupError('Generated key pair verification failed.')
            # Hard links fail if a destination appeared concurrently; never overwrite it.
            os.link(generated, private)
            os.link(Path(str(generated) + '.pub'), public)
    elif not public.exists():
        if not interactive:
            raise SetupError('Recovering a missing public key requires an interactive terminal.')
        print(f'🔒 Recovering the {role} public key; the private key stays unchanged.')
        result = subprocess.run(['ssh-keygen', '-y', '-f', str(private)], stdout=subprocess.PIPE,
                                text=True, check=True)
        with public.open('x') as output:
            output.write(result.stdout.rstrip() + '\n')
    if fingerprint(private, private=True) != fingerprint(public):
        raise SetupError('Private/public key mismatch; existing key contents were left untouched.')
    private.chmod(0o600)
    public.chmod(0o644)
    print(f'✅ {role.capitalize()} key pair ready (contents not displayed).')
    return public_material(public)


def confirm(message):
    return input(message + ' [y/N] ').strip().lower() in {'y', 'yes'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Do not forward an authorization header to a redirect destination.


class GitHub:
    def __init__(self, ask=confirm):
        self.ask = ask
        self.env = {name: value for name, value in os.environ.items()
                    if name not in {'GH_TOKEN', 'GITHUB_TOKEN', 'GH_ENTERPRISE_TOKEN', 'GITHUB_ENTERPRISE_TOKEN', 'GH_HOST', 'GH_DEBUG'}}

    def accounts(self):
        status = subprocess.run(['gh', 'auth', 'status', '--hostname', 'github.com', '--json', 'hosts'],
                                env=self.env, capture_output=True, text=True)
        try:
            if not status.stdout.strip() and 'not logged into any GitHub hosts' in status.stderr:
                accounts = []  # Some gh versions emit only this diagnostic before the first login.
            else:
                accounts = json.loads(status.stdout)['hosts'].get('github.com', [])
            if not isinstance(accounts, list) or any(not isinstance(account, dict) for account in accounts):
                raise ValueError('Unexpected account data')
        except (ValueError, KeyError, TypeError, AttributeError):
            raise SetupError('Could not inspect gh accounts safely. Log into the intended account manually and retry.')
        return accounts

    def token(self, login):
        def lookup(user):
            result = subprocess.run(['gh', 'auth', 'token', '--hostname', 'github.com', '--user', user],
                                    env=self.env, capture_output=True, text=True)
            return result.stdout.strip() if result.returncode == 0 else None
        token = lookup(login)
        if token:
            return token
        # GitHub logins are case-insensitive; the credential store may not be.
        for account in self.accounts():
            stored = account.get('login')
            if isinstance(stored, str) and stored.lower() == login.lower() and stored != login:
                return lookup(stored)
        return None

    def login(self, login):
        accounts = self.accounts()
        previous = next((account.get('login') for account in accounts if account.get('active')), None)
        if accounts and not previous:
            raise SetupError('Could not identify the prior active account; log into the intended account manually.')
        if not self.ask(f'Open browser login for GitHub account {login}?'):
            return None
        try:
            result = subprocess.run(['gh', 'auth', 'login', '--hostname', 'github.com', '--web',
                                     '--skip-ssh-key', '--git-protocol', 'ssh', '--scopes', 'admin:public_key'], env=self.env)
        finally:
            if previous:
                restored = subprocess.run(['gh', 'auth', 'switch', '--hostname', 'github.com', '--user', previous],
                                          env=self.env, capture_output=True)
                if restored.returncode:
                    raise SetupError('Restore the previous gh active account manually before continuing.')
        if result.returncode:
            raise SetupError('GitHub login did not complete; no key uploaded.')
        token = self.token(login)
        if not token:
            raise SetupError('The requested account was not authenticated; no key uploaded.')
        return token

    def request(self, token, method, path, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        request = urllib.request.Request('https://api.github.com' + path, data=payload, method=method,
                                         headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                                                  'Content-Type': 'application/json', 'User-Agent': 'dotfiles-ssh-setup'})
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            error.close()
            if error.code == 422:
                raise SetupError('GitHub rejected the key; it may belong to another account. No existing key was removed.') from None
            if error.code in (401, 403):
                raise SetupError('GitHub access denied. Authenticate the selected account with admin:public_key scope and retry.') from None
            raise SetupError(f'GitHub request failed (HTTP {error.code}); no automatic retry or credential output.') from None
        except (urllib.error.URLError, ValueError):
            raise SetupError('GitHub could not be reached or returned invalid data; retry later.') from None

    def register(self, login, key, role):
        login = github_user(login)
        token = self.token(login) or self.login(login)
        if not token:
            print(f'  ↪ {role.capitalize()} GitHub registration skipped.')
            return
        user = self.request(token, 'GET', '/user')
        if not isinstance(user, dict) or str(user.get('login', '')).lower() != login.lower():
            raise SetupError('Authenticated GitHub account does not match the requested login; no key uploaded.')
        page = 1
        while True:
            keys = self.request(token, 'GET', f'/user/keys?per_page=100&page={page}')
            if not isinstance(keys, list):
                raise SetupError('Could not verify existing GitHub keys; no key uploaded.')
            if any(isinstance(item, dict) and ' '.join(str(item.get('key', '')).split()[:2]) == key for item in keys):
                print(f'  ↪ {role.capitalize()} key already registered to the verified account.')
                return
            if len(keys) < 100:
                break
            page += 1
        if not self.ask(f'Upload the {role} public key to GitHub account {login}?'):
            print(f'  ↪ {role.capitalize()} GitHub registration skipped.')
            return
        self.request(token, 'POST', '/user/keys', {'title': 'dotfiles-' + role, 'key': key})
        print(f'✅ {role.capitalize()} public key registered to the verified account.')


def main():
    if sys.platform != 'darwin':
        raise SetupError('SSH setup supports macOS only.')
    os.umask(0o077)
    names = [key_name(os.environ.get(name, '')) for name in ['PERSONAL_KEY_NAME', 'WORK_KEY_NAME']]
    if names[0].lower() == names[1].lower():
        raise SetupError('Personal and work keys must use different filenames.')
    registration = os.environ.get('REGISTER_GITHUB_KEYS', 'true')
    if registration not in ('true', 'false'):
        raise SetupError('REGISTER_GITHUB_KEYS must be true or false.')
    logins = [os.environ.get(name, '') for name in ['PERSONAL_GITHUB_USER', 'WORK_GITHUB_USER']]
    if registration == 'true':
        for login in logins:
            if login:
                github_user(login)
    interactive = sys.stdin.isatty() and sys.stderr.isatty()
    directory = Path.home() / '.ssh'
    if directory.is_symlink():
        raise SetupError('The SSH directory is a symlink; review it manually before generating keys.')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    keys = [ensure_key(directory, name, role, interactive) for name, role in zip(names, ['personal', 'work'])]
    if registration == 'false':
        print('  ↪ GitHub registration disabled by local configuration.')
        return
    if not interactive:
        print('  ↪ GitHub registration needs account confirmation; rerun dotfiles ssh-keys in a terminal.')
        return
    if not shutil.which('gh'):
        raise SetupError('Keys are ready, but gh is missing. Install it through the reviewed Homebrew path and rerun.')
    client = GitHub()
    for role, key, login in zip(['personal', 'work'], keys, logins):
        login = login or input(f'GitHub login for the {role} key (blank to skip): ').strip()
        if login:
            client.register(login, key, role)
        else:
            print(f'  ↪ {role.capitalize()} GitHub registration skipped.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # CLI privacy boundary: unexpected tracebacks may contain credential/response data.
        message = str(error) if isinstance(error, SetupError) else 'SSH setup stopped; inspect local files/tools and rerun interactively.'
        print('❌ ' + message, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nSSH setup cancelled; existing keys were not replaced.', file=sys.stderr)
        sys.exit(130)
