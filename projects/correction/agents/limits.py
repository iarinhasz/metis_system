"""Limite compartilhado entre os pools e os ramos de um processo do worker."""

from collections.abc import Iterator
from contextlib import contextmanager
from threading import BoundedSemaphore, Lock

from projects.correction.agents.specs import Provider


class ProviderLimiter:
    def __init__(self, max_concurrency: int) -> None:
        if max_concurrency < 1:
            raise ValueError("A concorrência deve ser maior que zero.")
        self._semaphores = {provider: BoundedSemaphore(max_concurrency) for provider in Provider}

    @contextmanager
    def acquire(self, provider: Provider) -> Iterator[None]:
        with self._semaphores[provider]:
            yield


_shared: dict[int, ProviderLimiter] = {}
_shared_lock = Lock()


def shared_limiter(max_concurrency: int) -> ProviderLimiter:
    # cache/lru_cache permite duas construções concorrentes no primeiro acesso.
    with _shared_lock:
        if max_concurrency not in _shared:
            _shared[max_concurrency] = ProviderLimiter(max_concurrency)
        return _shared[max_concurrency]
