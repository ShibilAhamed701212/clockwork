"""
tests/test_packaging.py
------------------------
Unit tests for the Clockwork Packaging Engine (spec 07).

Run with:  pytest tests/test_packaging.py -v
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from clockwork.packaging.models import (
    PackageMetadata,
    CLOCKWORK_VERSION,
    PACKAGE_SCHEMA_VERSION,
    SENSITIVE_EXCLUSIONS,
)
from clockwork.packaging.checksum import (
    compute_file_checksum,
    compute_directory_checksum,
    write_checksum_file,
    verify_checksum_file,
    build_manifest,
)
from clockwork.packaging.packer import PackagingEngine, PackagingError
from clockwork.packaging.loader import PackageLoader, LoadError


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_clockwork_dir(root: Path) -> Path:
    """Create a minimal .clockwork directory suitable for packing."""
    cw = root / ".clockwork"
    cw.mkdir()
    (cw / "context.yaml").write_text("project: test\n", encoding="utf-8")
    (cw / "repo_map.json").write_text('{"files": []}', encoding="utf-8")
    (cw / "rules.md").write_text("# Rules\n", encoding="utf-8")
    (cw / "skills.json").write_text("[]", encoding="utf-8")
    handoff = cw / "handoff"
    handoff.mkdir()
    (handoff / "handoff.json").write_text('{"task": "none"}', encoding="utf-8")
    return cw


# ─────────────────────────────────────────────
# PackageMetadata Tests
# ─────────────────────────────────────────────

class TestPackageMetadata:
    def test_default_values(self):
        m = PackageMetadata()
        assert m.clockwork_version == CLOCKWORK_VERSION
        assert m.package_version == PACKAGE_SCHEMA_VERSION
        assert m.project_name == "unknown_project"

    def test_serialise_roundtrip(self):
        m = PackageMetadata(project_name="myproject")
        restored = PackageMetadata.from_json(m.to_json())
        assert restored.project_name == "myproject"
        assert restored.clockwork_version == m.clockwork_version

    def test_is_compatible_passes(self):
        m = PackageMetadata(
            clockwork_version=CLOCKWORK_VERSION,
            package_version=PACKAGE_SCHEMA_VERSION,
        )
        assert m.is_compatible() is True

    def test_is_compatible_fails_wrong_schema(self):
        m = PackageMetadata(package_version=999)
        assert m.is_compatible() is False

    def test_is_compatible_fails_wrong_version(self):
        m = PackageMetadata(clockwork_version="9.9")
        assert m.is_compatible() is False


# ─────────────────────────────────────────────
# Checksum Tests
# ─────────────────────────────────────────────

class TestChecksums:
    def test_file_checksum_stable(self, tmp_path):
        f = tmp_path / "a.txt"
        f.write_bytes(b"hello clockwork")
        c1 = compute_file_checksum(f)
        c2 = compute_file_checksum(f)
        assert c1 == c2
        assert len(c1) == 64  # sha256 hex

    def test_directory_checksum_stable(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa")
        (tmp_path / "b.txt").write_text("bbb")
        c1 = compute_directory_checksum(tmp_path)
        c2 = compute_directory_checksum(tmp_path)
        assert c1 == c2

    def test_directory_checksum_detects_change(self, tmp_path):
        (tmp_path / "a.txt").write_text("aaa")
        c1 = compute_directory_checksum(tmp_path)
        (tmp_path / "a.txt").write_text("CHANGED")
        c2 = compute_directory_checksum(tmp_path)
        assert c1 != c2

    def test_write_and_verify_checksum(self, tmp_path):
        cfile = tmp_path / "check.txt"
        write_checksum_file("abc123", cfile)
        assert verify_checksum_file("abc123", cfile) is True
        assert verify_checksum_file("wrong", cfile) is False

    def test_build_manifest_keys(self, tmp_path):
        (tmp_path / "x.json").write_text("{}")
        (tmp_path / "y.yaml").write_text("a: 1")
        manifest = build_manifest(tmp_path)
        assert set(manifest.keys()) == {"x.json", "y.yaml"}


# ─────────────────────────────────────────────
# PackagingEngine Tests
# ─────────────────────────────────────────────

class TestPackagingEngine:
    def test_pack_produces_file(self, tmp_path):
        _make_clockwork_dir(tmp_path)
        engine = PackagingEngine(repo_root=tmp_path, project_name="testproject")
        out = engine.pack()
        assert out.exists()
        assert out.suffix == ".clockwork"

    def test_pack_is_valid_zip(self, tmp_path):
        _make_clockwork_dir(tmp_path)
        engine = PackagingEngine(repo_root=tmp_path, project_name="testproject")
        out = engine.pack()
        assert zipfile.is_zipfile(out)

    def test_pack_contains_required_files(self, tmp_path):
        _make_clockwork_dir(tmp_path)
        engine = PackagingEngine(repo_root=tmp_path, project_name="testproject")
        out = engine.pack()
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert "context.yaml" in names
        assert "repo_map.json" in names
        assert "metadata.json" in names
        assert "package_checksum.txt" in names

    def test_pack_excludes_sensitive_files(self, tmp_path):
        cw = _make_clockwork_dir(tmp_path)
        (cw / ".env").write_text("SECRET=abc")
        (cw / "credentials.json").write_text('{"key": "secret"}')
        engine = PackagingEngine(repo_root=tmp_path, project_name="testproject")
        out = engine.pack()
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert ".env" not in names
        assert "credentials.json" not in names

    def test_pack_fails_without_init(self, tmp_path):
        engine = PackagingEngine(repo_root=tmp_path)
        with pytest.raises(PackagingError, match="not initialized"):
            engine.pack()

    def test_pack_fails_missing_required_files(self, tmp_path):
        (tmp_path / ".clockwork").mkdir()
        engine = PackagingEngine(repo_root=tmp_path)
        with pytest.raises(PackagingError, match="Required files missing"):
            engine.pack()

    def test_metadata_project_name(self, tmp_path):
        _make_clockwork_dir(tmp_path)
        engine = PackagingEngine(repo_root=tmp_path, project_name="myapp")
        out = engine.pack()
        with zipfile.ZipFile(out) as zf:
            meta = json.loads(zf.read("metadata.json"))
        assert meta["project_name"] == "myapp"

    def test_sensitive_filter(self):
        assert PackagingEngine._is_sensitive(".env") is True
        assert PackagingEngine._is_sensitive("credentials.json") is True
        assert PackagingEngine._is_sensitive("server.pem") is True
        assert PackagingEngine._is_sensitive("context.yaml") is False


# ─────────────────────────────────────────────
# PackageLoader Tests
# ─────────────────────────────────────────────

class TestPackageLoader:
    def _pack_and_get_path(self, repo: Path) -> Path:
        _make_clockwork_dir(repo)
        engine = PackagingEngine(repo_root=repo, project_name="proj")
        return engine.pack()

    def test_load_restores_files(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        pkg = self._pack_and_get_path(src)

        target = tmp_path / "target"
        target.mkdir()
        loader = PackageLoader(repo_root=target)
        loader.load(package_path=pkg)

        assert (target / ".clockwork" / "context.yaml").exists()
        assert (target / ".clockwork" / "repo_map.json").exists()

    def test_load_fails_on_missing_file(self, tmp_path):
        loader = PackageLoader(repo_root=tmp_path)
        with pytest.raises(LoadError, match="not found"):
            loader.load(package_path=tmp_path / "nonexistent.clockwork")

    def test_load_fails_on_corrupt_archive(self, tmp_path):
        bad = tmp_path / "bad.clockwork"
        bad.write_bytes(b"this is not a zip")
        loader = PackageLoader(repo_root=tmp_path)
        with pytest.raises(LoadError, match="valid .clockwork archive"):
            loader.load(package_path=bad)

    def test_load_fails_on_tampered_checksum(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        pkg = self._pack_and_get_path(src)

        # Tamper by rebuilding archive content to avoid duplicate ZIP entries.
        tampered = tmp_path / "tampered.clockwork"
        with zipfile.ZipFile(pkg, "r") as zin, zipfile.ZipFile(tampered, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "context.yaml":
                    data = b"tampered: true\n"
                zout.writestr(item, data)

        target = tmp_path / "target"
        target.mkdir()
        loader = PackageLoader(repo_root=target)
        with pytest.raises(LoadError, match="integrity check FAILED"):
            loader.load(package_path=tampered)

    def test_load_fails_incompatible_version(self, tmp_path):
        src = tmp_path / "source"
        src.mkdir()
        pkg = self._pack_and_get_path(src)

        # Patch metadata to incompatible version.
        # NOTE: the checksum recompute must happen AFTER the write context manager
        # exits, because ZipFile only finalises (writes end-of-central-directory)
        # on __exit__.  Reading the file while it is still open for writing raises
        # BadZipFile because the zip is not yet valid.
        import tempfile as _tempfile
        from clockwork.packaging.checksum import compute_directory_checksum as _cdc
        patched = tmp_path / "patched.clockwork"

        # Step 1: copy all entries except the old checksum, patching metadata.
        with zipfile.ZipFile(pkg, "r") as zin, zipfile.ZipFile(patched, "w") as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "metadata.json":
                    meta = json.loads(data)
                    meta["clockwork_version"] = "99.0"
                    meta["package_version"] = 999
                    data = json.dumps(meta).encode()
                if item.filename != "package_checksum.txt":
                    zout.writestr(item, data)
        # zout is now closed and the zip is finalised.

        # Step 2: recompute checksum from the now-valid zip, then append it.
        with _tempfile.TemporaryDirectory() as td:
            zipfile.ZipFile(patched).extractall(td)
            chk = _cdc(Path(td))
        with zipfile.ZipFile(patched, "a") as zappend:
            zappend.writestr("package_checksum.txt", chk)

        target = tmp_path / "target"
        target.mkdir()
        loader = PackageLoader(repo_root=target)
        with pytest.raises(LoadError, match="Incompatible package version"):
            loader.load(package_path=patched)
