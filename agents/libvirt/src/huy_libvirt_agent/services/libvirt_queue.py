"""Serialize libvirt API calls to avoid overloading the hypervisor."""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from collections.abc import Callable
from typing import TypeVar

import structlog

from huy_libvirt_agent.services.libvirt_client import LibvirtError

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class LibvirtQueue:
    """Run libvirt work on a bounded thread pool (default: one worker)."""

    def __init__(
        self,
        *,
        workers: int = 1,
        max_pending: int = 64,
        call_timeout_seconds: float = 300.0,
    ) -> None:
        if workers < 1:
            raise ValueError("libvirt queue workers must be >= 1")
        if max_pending < 1:
            raise ValueError("libvirt queue max_pending must be >= 1")
        self._workers = workers
        self._max_pending = max_pending
        self._call_timeout = call_timeout_seconds
        self._pending = 0
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="huy-libvirt",
        )

    @property
    def workers(self) -> int:
        return self._workers

    @property
    def max_pending(self) -> int:
        return self._max_pending

    @property
    def pending(self) -> int:
        with self._lock:
            return self._pending

    def run(self, fn: Callable[..., T], /, *args, **kwargs) -> T:
        """Enqueue a call; block until it completes or times out."""
        self._acquire_slot()
        try:
            future = self._executor.submit(lambda: fn(*args, **kwargs))
            try:
                return future.result(timeout=self._call_timeout)
            except concurrent.futures.TimeoutError as exc:
                future.cancel()
                raise LibvirtError(
                    f"Libvirt call timed out after {self._call_timeout}s",
                    "LIBVIRT_QUEUE_TIMEOUT",
                ) from exc
        finally:
            self._release_slot()

    async def run_async(self, fn: Callable[..., T], /, *args, **kwargs) -> T:
        """Async wrapper that does not block the event loop while waiting."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.run(fn, *args, **kwargs),
        )

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=not wait)
        logger.info("libvirt_queue_shutdown", workers=self._workers)

    def _acquire_slot(self) -> None:
        with self._lock:
            if self._pending >= self._max_pending:
                logger.warning(
                    "libvirt_queue_full",
                    pending=self._pending,
                    max_pending=self._max_pending,
                )
                raise LibvirtError(
                    f"Libvirt queue full ({self._max_pending} pending calls)",
                    "LIBVIRT_QUEUE_FULL",
                )
            self._pending += 1

    def _release_slot(self) -> None:
        with self._lock:
            self._pending -= 1
