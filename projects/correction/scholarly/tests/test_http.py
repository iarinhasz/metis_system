"""Retry HTTP, mapeamento de erros transitórios e rate limit concorrente."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, nullcontext
from threading import Lock
from time import monotonic, sleep

import pytest

from projects.correction.pipeline.errors import TransientStageError
from projects.correction.scholarly.cache import DOIResponseCache
from projects.correction.scholarly.errors import ScholarlyClientError, ScholarlyTransientError
from projects.correction.scholarly.http import ScholarlyHTTPClient
from projects.correction.scholarly.rate_limit import RedisTokenBucket
from projects.correction.scholarly.tests.http_stub import StubResponse, api_stub
from projects.correction.scholarly.tests.test_support import MemoryRedis, monotonic_seconds


class NoopLimiter:
    def acquire(self, provider: str, *, rate: float | None = None, capacity: int = 1) -> None:
        del provider, rate, capacity

    def permit(self, provider: str) -> AbstractContextManager[None]:
        del provider
        return nullcontext()


def http_client(
    *,
    retries: int = 3,
    sleeps: list[float] | None = None,
) -> ScholarlyHTTPClient:
    redis = MemoryRedis()
    return ScholarlyHTTPClient(
        "crossref",
        max_retries=retries,
        limiter=NoopLimiter(),
        cache=DOIResponseCache(redis),
        redis_client=redis,
        sleeper=(sleeps.append if sleeps is not None else lambda delay: None),
    )


def test_429_waits_for_retry_after_then_succeeds() -> None:
    delays: list[float] = []
    with api_stub() as api:
        api.queue(
            StubResponse(b"rate limited", 429, {"Retry-After": "2"}),
            StubResponse(b'{"message":{}}'),
        )
        response = http_client(sleeps=delays).get(api.url)

    assert response is not None and response.status == 200
    assert len(api.requests) == 2
    assert delays == [2.0]


def test_exhausted_5xx_raises_transient_stage_error() -> None:
    with api_stub() as api:
        api.queue(*(StubResponse(b"unavailable", 503) for _ in range(3)))
        with pytest.raises(ScholarlyTransientError) as error:
            http_client(retries=2).get(api.url)
    assert isinstance(error.value, TransientStageError)
    assert len(api.requests) == 3


def test_non_retryable_4xx_raises_scholarly_client_error() -> None:
    with api_stub() as api:
        api.queue(StubResponse(b"bad request", 400))
        with pytest.raises(ScholarlyClientError):
            http_client().get(api.url)
    assert len(api.requests) == 1


def test_token_bucket_serializes_concurrent_requests_at_configured_rate() -> None:
    redis = MemoryRedis()
    limiter = RedisTokenBucket(redis, clock=monotonic_seconds, sleeper=sleep)
    request_times: list[float] = []

    def request() -> None:
        limiter.acquire("crossref", rate=25, capacity=1)
        request_times.append(monotonic())

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda _: request(), range(5)))

    ordered_times = sorted(request_times)
    intervals = [
        later - earlier for earlier, later in zip(ordered_times, ordered_times[1:], strict=False)
    ]
    assert len(request_times) == 5
    assert all(interval >= 0.035 for interval in intervals)


def test_crossref_concurrent_requests_respect_three_in_flight_limit() -> None:
    limiter = RedisTokenBucket(
        MemoryRedis(),
        clock=monotonic_seconds,
        sleeper=sleep,
        concurrency_poll_seconds=0.005,
    )
    guard = Lock()
    active = 0
    maximum_active = 0

    def request() -> None:
        nonlocal active, maximum_active
        with limiter.permit("crossref"):
            with guard:
                active += 1
                maximum_active = max(maximum_active, active)
            sleep(0.03)
            with guard:
                active -= 1

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: request(), range(8)))

    assert 1 < maximum_active <= 3
