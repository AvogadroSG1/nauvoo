from __future__ import annotations

from pathlib import Path

from nauvoo.ports.driven.vault_reader import VaultReaderPort


class FilesystemVaultAdapter(VaultReaderPort):
    def __init__(self, vault_dir: Path) -> None:
        self._vault_dir = vault_dir

    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> None:
        Path(path).write_text(content, encoding="utf-8")

    def list_md_files(self) -> list[str]:
        return [str(p) for p in self._vault_dir.rglob("*.md")]
