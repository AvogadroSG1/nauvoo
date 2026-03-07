from __future__ import annotations

import contextlib
import logging
import os
import threading
from collections.abc import Callable

from nauvoo.ports.driven.vault_reader import VaultReaderPort
from nauvoo.ports.driving.vault_watcher import VaultWatcherPort

logger = logging.getLogger(__name__)


class PollingWatcherAdapter(VaultWatcherPort):
    def __init__(self, vault: VaultReaderPort, interval: float = 30.0) -> None:
        self._vault = vault
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._mtimes: dict[str, float] = {}

    def start(self, on_change: Callable[[list[str]], None]) -> None:
        self._stop_event.clear()
        self._mtimes = self._snapshot()
        self._thread = threading.Thread(
            target=self._poll_loop, args=(on_change,), daemon=True
        )
        self._thread.start()
        logger.info("PollingWatcher started (interval=%.0fs)", self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval + 1)

    def _poll_loop(self, on_change: Callable[[list[str]], None]) -> None:
        while not self._stop_event.wait(timeout=self._interval):
            try:
                current = self._snapshot()
                changed = [
                    path
                    for path, mtime in current.items()
                    if self._mtimes.get(path) != mtime
                ]
                self._mtimes = current
                if changed:
                    on_change(changed)
            except Exception:
                logger.exception("Error during poll")

    def _snapshot(self) -> dict[str, float]:
        result = {}
        for path in self._vault.list_md_files():
            with contextlib.suppress(OSError):
                result[path] = os.path.getmtime(path)
        return result
