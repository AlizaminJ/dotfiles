#!/usr/bin/env python3
"""Prepare local SSH keys and print commands for manual GitHub registration."""

import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


class SetupError(Exception):
    pass


def key_name(value):
    reserved = {'config', 'known_hosts', 'known_hosts.old', 'authorized_keys', 'environment', 'rc'}
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}', value) or value.lower() in reserved or value.lower().endswith('.pub'):
        raise SetupError('SSH key names must be distinct, ordinary filenames, not SSH config files or .pub names.')
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
    return material


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


def main():
    os.umask(0o077)
    names = [key_name(os.environ.get(name, '')) for name in ['PERSONAL_KEY_NAME', 'WORK_KEY_NAME']]
    if names[0].lower() == names[1].lower():
        raise SetupError('Personal and work keys must use different filenames.')
    interactive = sys.stdin.isatty() and sys.stderr.isatty()
    directory = Path.home() / '.ssh'
    if directory.is_symlink():
        raise SetupError('The SSH directory is a symlink; review it manually before generating keys.')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    for name, role in zip(names, ['personal', 'work']):
        ensure_key(directory, name, role, interactive)
    copy_command = 'pbcopy' if sys.platform == 'darwin' else 'wl-copy  # or: xclip -selection clipboard'
    print('🔒 Add each public key manually to its matching GitHub account:')
    for name, role in zip(names, ['personal', 'work']):
        print(f'  ↪ {role.capitalize()}: {copy_command} < "$HOME/.ssh/{name}.pub"')
    print('  ↪ Sign into the matching account and open https://github.com/settings/ssh/new')
    print('  ↪ Choose Authentication Key, paste the public key, and save. Repeat for the other account.')
    print('  ↪ Commands were printed only; nothing was copied, opened, or uploaded.')


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
