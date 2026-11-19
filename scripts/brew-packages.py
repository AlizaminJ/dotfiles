#!/usr/bin/env python3
"""Fail closed unless new Homebrew recipes have verifiable, sufficiently old sources.

We check recipe edit dates, not binary release dates. Existing installations
and dependencies bundled inside binaries aren't checked here.
"""

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request


ENV = dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_INSTALL_CLEANUP="1",
           HOMEBREW_NO_INSTALL_UPGRADE="1", HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK="1")


def brew(*args):
    return subprocess.check_output(["brew", *args], env=ENV, text=True)


def github(path):
    # gh uses its credential store without putting tokens in arguments or logs.
    if shutil.which("gh"):
        result = subprocess.run(
            ["gh", "api", path, "-H", "Accept: application/vnd.github+json"],
            capture_output=True,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    request = urllib.request.Request(
        "https://api.github.com/" + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "dotfiles-age-check"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    return json.loads(data)


def recipe_age(record, kind, now):
    tap = record["tap"]
    if tap not in ("homebrew/core", "homebrew/cask"):
        raise ValueError("Third-party taps require a separate source and dependency review")
    repo = "Homebrew/homebrew-" + ("core" if kind == "formula" else "cask")
    path = record["ruby_source_path"]
    commits = github(f"repos/{repo}/commits?path={urllib.parse.quote(path)}&per_page=1")
    if not commits:
        raise ValueError("Recipe publication history could not be established")
    commit = commits[0]
    date = dt.datetime.fromisoformat(commit["commit"]["committer"]["date"].replace("Z", "+00:00"))
    if now - date < dt.timedelta(days=7):
        raise ValueError(f"Recipe changed less than 7 days ago ({date.date()}); wait or review an older immutable recipe")
    # Raw CLI output can render control bytes as visible text, changing the hash.
    # JSON's base64 content preserves the original bytes through terminal filtering.
    contents = github(f"repos/{repo}/contents/{path}?ref={commit['sha']}")
    if contents.get("encoding") != "base64" or contents.get("type") != "file":
        raise ValueError("Original recipe bytes could not be retrieved")
    source = base64.b64decode("".join(contents["content"].split()), validate=True)
    expected = record["ruby_source_checksum"]["sha256"]
    if hashlib.sha256(source).hexdigest() != expected:
        raise ValueError("Current Homebrew recipe does not match the age-checked immutable source")
    if kind == "cask" and re.search(rb"^\s*(?:preflight(?:_steps)?|postflight(?:_steps)?|installer|pkg)\b", source, re.MULTILINE):
        raise ValueError("Cask installer packages or hooks require explicit approval")
    return commit["sha"], date.isoformat()


def plan(brewfile, now):
    requested = []
    for line in Path(brewfile).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r'\s*(brew|cask)\s+"([\w@+./-]+)"\s*(?:#.*)?', line)
        if not match:
            raise ValueError("Unsupported Brewfile entry; review its installer before extending this checker")
        requested.append(("formula" if match[1] == "brew" else "cask", match[2]))
    pending, seen = [], set()
    while requested:
        kind, name = requested.pop(0)
        if (kind, name) in seen:
            continue
        seen.add((kind, name))
        data = json.loads(brew("info", "--json=v2", "--" + kind, name))
        record = data["formulae" if kind == "formula" else "casks"][0]
        # Existing installations are not upgraded or retroactively audited here.
        if record.get("installed"):
            continue
        if record.get("disabled"):
            raise ValueError(f"{name} is disabled by Homebrew: {record.get('disable_reason')}")
        if kind == "formula" and record.get("post_install_defined"):
            raise ValueError(f"{name} defines a post-install hook; explicit approval required")
        if kind == "formula" and not record.get("bottle", {}).get("stable"):
            raise ValueError(f"{name} has no bottle; source builds need a separate build-dependency review")
        try:
            revision, date = recipe_age(record, kind, now)
        except ValueError as error:
            raise ValueError(f"{name}: {error}") from error
        version = record["versions"]["stable"] if kind == "formula" else record["version"]
        if kind == "formula":
            dependencies = [("formula", dep) for dep in record.get("dependencies", [])]
            dependencies += [("formula", dep) for dep in record.get("recommended_dependencies", [])]
        else:
            deps = record.get("depends_on") or {}
            dependencies = [("formula", dep) for dep in deps.get("formula", [])]
            dependencies += [("cask", dep) for dep in deps.get("cask", [])]
        pending.append({"kind": kind, "name": name, "version": version,
                        "source_sha256": record["ruby_source_checksum"]["sha256"],
                        "recipe_commit": revision, "recipe_date": date,
                        "dependencies": dependencies})
        requested.extend(dependencies)
    records = {(item["kind"], item["name"]): item for item in pending}
    ordered, visited, visiting = [], set(), set()

    def visit(key):
        if key in visiting:
            raise ValueError("Dependency cycle requires a separate review")
        if key in visited or key not in records:
            return
        visiting.add(key)
        for dep in records[key]["dependencies"]:
            visit(dep)
        visiting.remove(key)
        visited.add(key)
        ordered.append(records[key])

    for key in records:
        visit(key)
    return ordered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brewfile")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This Homebrew dependency check currently supports macOS only")
    pending = plan(args.brewfile, dt.datetime.now(dt.timezone.utc))
    for item in pending:
        print(f"✅ {item['name']} {item['version']}: exact recipe unchanged for at least 7 days")
    if not args.install:
        return
    # Recheck the resolved versions and hashes before executing any installation.
    for item in pending:
        data = json.loads(brew("info", "--json=v2", "--" + item["kind"], item["name"]))
        record = data["formulae" if item["kind"] == "formula" else "casks"][0]
        version = record["versions"]["stable"] if item["kind"] == "formula" else record["version"]
        if record["ruby_source_checksum"]["sha256"] != item["source_sha256"] or version != item["version"]:
            raise ValueError("Homebrew metadata changed after review; refusing installation")
    # Retain the reviewed selection even if a later installation fails partway through.
    if pending:
        state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "dotfiles"
        state.mkdir(parents=True, exist_ok=True)
        target = state / "brew-review.json"
        old = json.loads(target.read_text()) if target.exists() else []
        target.write_text(json.dumps(old + pending, indent=2) + "\n")
    for item in pending:
        # Dependencies are already ordered and reviewed; do not let brew select new ones.
        options = ["--force-bottle", "--ignore-dependencies"] if item["kind"] == "formula" else ["--skip-cask-deps"]
        subprocess.run(["brew", "install", "--" + item["kind"], *options, item["name"]], env=ENV, check=True)
        if item["kind"] == "formula":
            subprocess.run(["brew", "pin", item["name"]], env=ENV, check=True)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"❌ Homebrew install stopped: {error}", file=sys.stderr)
        sys.exit(1)
