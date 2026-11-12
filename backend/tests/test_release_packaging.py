"""Protect the downloadable release against leaks and incomplete distributions."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("package_release", ROOT / "scripts/package_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleasePackagingTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".reports" / "packaging-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(scratch.resolve())
        self.addCleanup(self.temp.cleanup)
        self.write("package.json", '{"version":"1.2.3"}')
        self.write("frontend/package.json", '{"version":"1.2.3"}')
        self.write("backend/pyproject.toml", '[project]\nversion = "1.2.3"\n')
        self.write("frontend/dist/index.html", '<div id="root"></div>')
        self.write("frontend/dist/assets/app.js", 'fetch("/v2/capabilities")')

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def build(self, output="release"):
        return release.package("v1.2.3", self.root / output, self.root / "frontend/dist", "test-commit", self.root)

    def test_bundle_contains_application_and_build_but_excludes_private_files(self):
        expected = {
            "backend/main.py", "backend/cadrix_v2/registry.py", "backend/uv.lock",
            "frontend/src/App.jsx", "frontend/dist/index.html", "frontend/dist/assets/app.js",
            "frontend/.env.example", ".env.example", ".github/workflows/ci.yml", "scripts/dev.mjs",
        }
        for name in expected - {"frontend/dist/index.html", "frontend/dist/assets/app.js"}:
            self.write(name, "included")
        private = {
            ".env", "backend/.env.production", "frontend/src/.env.local", "backend/out/private.step",
            "backend/cadrix_v2/__pycache__/cached.pyc", "frontend/node_modules/private.js",
            "scripts/.venv-ci/private.txt", "scripts/debug.log", ".git/config", ".reports/private.txt",
        }
        for name in private:
            self.write(name, "SECRET-MUST-NOT-SHIP")
        with zipfile.ZipFile(self.build()) as bundle:
            names = {name.removeprefix("cadrixai-1.2.3/") for name in bundle.namelist()}
            self.assertTrue(expected <= names, expected - names)
            self.assertFalse(private & names)
            for name in bundle.namelist():
                self.assertNotIn(b"SECRET-MUST-NOT-SHIP", bundle.read(name))

    def test_manifest_checksums_and_archive_are_reproducible(self):
        first = self.build("first")
        second = self.build("second")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        digest, filename = (first.parent / "SHA256SUMS").read_text().split()
        self.assertEqual(digest, hashlib.sha256(first.read_bytes()).hexdigest())
        self.assertEqual(filename, first.name)
        with zipfile.ZipFile(first) as bundle:
            manifest = json.loads(bundle.read("cadrixai-1.2.3/release-manifest.json"))
            self.assertEqual(manifest["commit"], "test-commit")
            for name, expected in manifest["files"].items():
                self.assertEqual(hashlib.sha256(bundle.read("cadrixai-1.2.3/" + name)).hexdigest(), expected)

    def test_release_rejects_mismatched_or_unsafe_tags(self):
        for tag in ("v1.2.4", "1.2.3", "v1.2.3-rc.1", "v01.2.3", "../../private"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.validate_version(tag, self.root)
        self.write("frontend/package.json", '{"version":"2.0.0"}')
        with self.assertRaisesRegex(ValueError, "must match"):
            self.build()

    def test_missing_frontend_build_fails_before_publishing(self):
        with self.assertRaisesRegex(ValueError, "Build the frontend"):
            release.package("v1.2.3", self.root / "release", self.root / "not-built", root=self.root)


if __name__ == "__main__":
    unittest.main()
