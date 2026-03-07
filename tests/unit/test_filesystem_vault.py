from __future__ import annotations

from pathlib import Path

from nauvoo.adapters.driven.filesystem_vault import FilesystemVaultAdapter


def test_read_write_roundtrip(tmp_path):
    adapter = FilesystemVaultAdapter(vault_dir=tmp_path)
    (tmp_path / "doc.md").write_text("hello", encoding="utf-8")
    assert adapter.read_file(str(tmp_path / "doc.md")) == "hello"
    adapter.write_file(str(tmp_path / "doc.md"), "updated")
    assert (tmp_path / "doc.md").read_text(encoding="utf-8") == "updated"


def test_list_md_files(tmp_path):
    (tmp_path / "a.md").write_text("", encoding="utf-8")
    (tmp_path / "b.md").write_text("", encoding="utf-8")
    (tmp_path / "other.txt").write_text("", encoding="utf-8")
    adapter = FilesystemVaultAdapter(vault_dir=tmp_path)
    files = adapter.list_md_files()
    names = {Path(f).name for f in files}
    assert names == {"a.md", "b.md"}


def test_list_md_files_recursive(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "nested.md").write_text("", encoding="utf-8")
    (tmp_path / "top.md").write_text("", encoding="utf-8")
    adapter = FilesystemVaultAdapter(vault_dir=tmp_path)
    files = adapter.list_md_files()
    names = {Path(f).name for f in files}
    assert names == {"nested.md", "top.md"}
