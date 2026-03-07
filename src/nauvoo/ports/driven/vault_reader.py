from __future__ import annotations

from abc import ABC, abstractmethod


class VaultReaderPort(ABC):
    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read a markdown file's content."""

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write (overwrite) a markdown file's content."""

    @abstractmethod
    def list_md_files(self) -> list[str]:
        """Return absolute paths of all .md files in the watched directory."""
