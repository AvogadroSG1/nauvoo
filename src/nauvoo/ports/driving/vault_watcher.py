from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable


class VaultWatcherPort(ABC):
    @abstractmethod
    def start(self, on_change: Callable[[list[str]], None]) -> None:
        """Start watching. Calls on_change with list of changed file paths."""

    @abstractmethod
    def stop(self) -> None:
        """Stop watching."""
