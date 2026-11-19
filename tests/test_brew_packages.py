"""Package-age checks must fail closed, including for transitive dependencies."""

import base64
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brew_packages", REPO / "scripts/brew-packages.py")
brew_packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brew_packages)
NOW = dt.datetime(2026, 11, 9, tzinfo=dt.timezone.utc)
SOURCE = b'class Example < Formula\nend\n'


def contents(source):
    return {"type": "file", "encoding": "base64", "content": base64.encodebytes(source).decode()}


def record(name="example", **overrides):
    result = dict(
        name=name, tap="homebrew/core", installed=[], disabled=False,
        versions={"stable": "1.0.0"}, bottle={"stable": {"files": {}}},
        dependencies=[], recommended_dependencies=[], ruby_source_path=f"Formula/{name[0]}/{name}.rb",
        ruby_source_checksum={"sha256": hashlib.sha256(SOURCE).hexdigest()},
    )
    result.update(overrides)
    return result


class BrewAgeTest(unittest.TestCase):
    def test_accepts_exact_old_recipe(self):
        history = [{"sha": "abc", "commit": {"committer": {"date": "2026-10-01T00:00:00Z"}}}]
        with patch.object(brew_packages, "github", side_effect=[history, contents(SOURCE)]):
            self.assertEqual(brew_packages.recipe_age(record(), "formula", NOW)[0], "abc")

    def test_rejects_recent_recipe_before_downloading_source(self):
        history = [{"sha": "abc", "commit": {"committer": {"date": "2026-11-08T00:00:00Z"}}}]
        with patch.object(brew_packages, "github", return_value=history) as api:
            with self.assertRaisesRegex(ValueError, "less than 7 days"):
                brew_packages.recipe_age(record(), "formula", NOW)
            self.assertEqual(api.call_count, 1)

    def test_rejects_source_hash_mismatch(self):
        history = [{"sha": "abc", "commit": {"committer": {"date": "2026-10-01T00:00:00Z"}}}]
        with patch.object(brew_packages, "github", side_effect=[history, contents(b"different")]):
            with self.assertRaisesRegex(ValueError, "does not match"):
                brew_packages.recipe_age(record(), "formula", NOW)

    def test_preserves_escape_bytes_in_recipe_hash(self):
        source = b'assert_equal "\x1b[1;32m prompt\x1b[0m"\n'
        recipe = record(ruby_source_checksum={"sha256": hashlib.sha256(source).hexdigest()})
        history = [{"sha": "abc", "commit": {"committer": {"date": "2026-10-01T00:00:00Z"}}}]
        with patch.object(brew_packages, "github", side_effect=[history, contents(source)]) as api:
            self.assertEqual(brew_packages.recipe_age(recipe, "formula", NOW)[0], "abc")
            self.assertEqual(api.call_args.args, ("repos/Homebrew/homebrew-core/contents/Formula/e/example.rb?ref=abc",))
            self.assertEqual(api.call_args.kwargs, {})

    def test_rejects_unexpected_source_encoding(self):
        history = [{"sha": "abc", "commit": {"committer": {"date": "2026-10-01T00:00:00Z"}}}]
        with patch.object(brew_packages, "github", side_effect=[history, {"type": "file", "encoding": "none"}]):
            with self.assertRaisesRegex(ValueError, "Original recipe bytes"):
                brew_packages.recipe_age(record(), "formula", NOW)

    def test_cask_install_hooks_and_declarative_steps_require_review(self):
        history = [{'sha': 'abc', 'commit': {'committer': {'date': '2026-10-01T00:00:00Z'}}}]
        for keyword in ['preflight', 'postflight', 'preflight_steps', 'postflight_steps', 'installer', 'pkg']:
            source = f'cask "example" do\n  {keyword} do\n  end\nend\n'.encode()
            recipe = record(tap='homebrew/cask', ruby_source_path='Casks/e/example.rb',
                            ruby_source_checksum={'sha256': hashlib.sha256(source).hexdigest()})
            with self.subTest(keyword=keyword), patch.object(brew_packages, 'github', side_effect=[history, contents(source)]):
                with self.assertRaisesRegex(ValueError, 'hooks require explicit approval'):
                    brew_packages.recipe_age(recipe, 'cask', NOW)

    def test_checks_transitive_dependencies_and_orders_them_first(self):
        with tempfile.TemporaryDirectory() as directory:
            brewfile = Path(directory) / "Brewfile"
            brewfile.write_text('brew "example"\n')
            records = {"example": record(dependencies=["dependency"]), "dependency": record("dependency")}
            with patch.object(brew_packages, "brew", side_effect=lambda *args: json.dumps({"formulae": [records[args[-1]]]})), \
                 patch.object(brew_packages, "recipe_age", return_value=("abc", "old")) as check:
                planned = brew_packages.plan(brewfile, NOW)
                self.assertEqual([item["name"] for item in planned], ["dependency", "example"])
                self.assertEqual(check.call_count, 2)
            with patch.object(brew_packages, "brew", side_effect=lambda *args: json.dumps({"formulae": [records[args[-1]]]})), \
                 patch.object(brew_packages, "recipe_age", side_effect=[("abc", "old"), ValueError("dependency too new")]):
                with self.assertRaisesRegex(ValueError, "dependency too new"):
                    brew_packages.plan(brewfile, NOW)

    def test_installed_packages_are_not_upgraded_or_reaudited(self):
        with tempfile.TemporaryDirectory() as directory:
            brewfile = Path(directory) / "Brewfile"
            brewfile.write_text('brew "example"\n')
            with patch.object(brew_packages, "brew", return_value=json.dumps({"formulae": [record(installed=[{"version": "0.9"}])]})), \
                 patch.object(brew_packages, "recipe_age") as check:
                self.assertEqual(brew_packages.plan(brewfile, NOW), [])
                check.assert_not_called()

    def test_source_builds_and_post_install_hooks_require_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            brewfile = Path(directory) / "Brewfile"
            brewfile.write_text('brew "example"\n')
            for recipe in [record(bottle={}), record(post_install_defined=True), record(disabled=True)]:
                with self.subTest(recipe=recipe), patch.object(brew_packages, "brew", return_value=json.dumps({"formulae": [recipe]})):
                    with self.assertRaises(ValueError):
                        brew_packages.plan(brewfile, NOW)


if __name__ == "__main__":
    unittest.main()
