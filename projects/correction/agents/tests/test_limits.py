"""Concorrência real entre threads, inclusive após uma exceção."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest

from projects.correction.agents.factory import AgentFactory
from projects.correction.agents.limits import ProviderLimiter, shared_limiter
from projects.correction.agents.specs import Provider


def test_parallel_callers_never_exceed_provider_limit() -> None:
    limiter = ProviderLimiter(3)
    start = Barrier(12)
    lock = Lock()
    active = peak = 0

    def invoke(index: int) -> int:
        nonlocal active, peak
        start.wait(timeout=5)
        with limiter.acquire(Provider.GOOGLE):
            with lock:
                active += 1
                peak = max(peak, active)
            Event().wait(0.01)
            with lock:
                active -= 1
        return index

    with ThreadPoolExecutor(max_workers=12) as pool:
        assert list(pool.map(invoke, range(12))) == list(range(12))
    assert peak == 3 and active == 0


def test_one_provider_does_not_block_the_other() -> None:
    limiter = ProviderLimiter(1)

    def google() -> bool:
        with limiter.acquire(Provider.GOOGLE):
            return True

    with limiter.acquire(Provider.OPENAI), ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(google).result(timeout=2)


def test_exception_releases_the_slot() -> None:
    limiter = ProviderLimiter(1)
    with pytest.raises(RuntimeError), limiter.acquire(Provider.OPENAI):
        raise RuntimeError("sintético")
    with ThreadPoolExecutor(max_workers=1) as pool:

        def invoke() -> bool:
            with limiter.acquire(Provider.OPENAI):
                return True

        assert pool.submit(invoke).result(timeout=2)


def test_invalid_limit() -> None:
    with pytest.raises(ValueError):
        ProviderLimiter(0)


def test_concurrent_first_access_gets_one_limiter_for_all_factories() -> None:
    start = Barrier(12)

    def get_limiter(index: int) -> ProviderLimiter:
        start.wait(timeout=5)
        return shared_limiter(17)

    with ThreadPoolExecutor(max_workers=12) as pool:
        limiters = list(pool.map(get_limiter, range(12)))
    assert all(limiter is limiters[0] for limiter in limiters)
    assert AgentFactory("a", "test").limiter is AgentFactory("b", "test").limiter
