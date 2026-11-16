"""Rate limit distribuído por provedor usando token bucket no Redis."""

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from time import sleep
from typing import Protocol
from uuid import uuid4

from redis import Redis


class RedisRateLimitClient(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: str | int | float) -> int: ...

    def time(self) -> tuple[int, int]: ...


class RateLimiter(Protocol):
    def acquire(self, provider: str, *, rate: float | None = None, capacity: int = 1) -> None: ...

    def permit(self, provider: str) -> AbstractContextManager[None]: ...


_ACQUIRE_TOKEN = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local capacity = tonumber(ARGV[3])
local interval = 1 / rate
local tolerance = (capacity - 1) * interval
local theoretical_arrival = tonumber(redis.call('GET', key)) or now
local wait = math.max(0, theoretical_arrival - tolerance - now)
theoretical_arrival = math.max(now, theoretical_arrival) + interval
local ttl = math.ceil(theoretical_arrival - now + tolerance + 60000)
redis.call('SET', key, theoretical_arrival, 'PX', ttl)
return math.ceil(wait * 1000)
"""

_ACQUIRE_SLOT = """
local owner = ARGV[1]
local ttl = tonumber(ARGV[2])
for index, key in ipairs(KEYS) do
    if redis.call('SET', key, owner, 'NX', 'PX', ttl) then
        return index
    end
end
return 0
"""

_RELEASE_SLOT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

PROVIDER_RATES: dict[str, float] = {
    "crossref": 3.0,
    "openalex": 30.0,
    "semantic_scholar": 1.0,
    "arxiv": 1 / 3,
    "unpaywall": 100_000 / 86_400,
}

PROVIDER_MAX_CONCURRENCY: dict[str, int] = {"crossref": 3}


class RedisTokenBucket:
    """Adquire permissões por provedor; o relógio Redis mantém workers sincronizados."""

    def __init__(
        self,
        client: RedisRateLimitClient,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] = sleep,
        prefix: str = "metis:scholarly:rate",
        concurrency_prefix: str = "metis:scholarly:in-flight",
        concurrency_lease_seconds: int = 60,
        concurrency_poll_seconds: float = 0.05,
    ) -> None:
        if concurrency_lease_seconds <= 0 or concurrency_poll_seconds <= 0:
            raise ValueError("Lease e intervalo de polling precisam ser positivos.")
        self.client = client
        self.clock = clock or self._redis_clock
        self.sleeper = sleeper
        self.prefix = prefix
        self.concurrency_prefix = concurrency_prefix
        self.concurrency_lease_seconds = concurrency_lease_seconds
        self.concurrency_poll_seconds = concurrency_poll_seconds

    @classmethod
    def from_url(cls, url: str) -> RedisTokenBucket:
        return cls(Redis.from_url(url))

    def _redis_clock(self) -> float:
        seconds, microseconds = self.client.time()
        return seconds + microseconds / 1_000_000

    def acquire(self, provider: str, *, rate: float | None = None, capacity: int = 1) -> None:
        provider_rate = PROVIDER_RATES[provider] if rate is None else rate
        if provider_rate <= 0 or capacity < 1:
            raise ValueError("A taxa e a capacidade do token bucket devem ser positivas.")
        wait_ms = self.client.eval(
            _ACQUIRE_TOKEN,
            1,
            f"{self.prefix}:{provider}",
            self.clock(),
            provider_rate,
            capacity,
        )
        if wait_ms > 0:
            self.sleeper(wait_ms / 1000)

    @contextmanager
    def permit(self, provider: str) -> Iterator[None]:
        limit = PROVIDER_MAX_CONCURRENCY.get(provider)
        if limit is None:
            yield
            return

        owner = uuid4().hex
        keys = [f"{self.concurrency_prefix}:{provider}:{slot}" for slot in range(limit)]
        slot = 0
        while slot == 0:
            slot = self.client.eval(
                _ACQUIRE_SLOT,
                limit,
                *keys,
                owner,
                self.concurrency_lease_seconds * 1000,
            )
            if slot == 0:
                self.sleeper(self.concurrency_poll_seconds)
        try:
            yield
        finally:
            self.client.eval(_RELEASE_SLOT, 1, keys[slot - 1], owner)
